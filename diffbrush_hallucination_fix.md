# DiffBrush hallucinatie fix

## Het probleem

De gegenereerde adresblokken zagen er zo uit:

```
KAZOL 6acKowssskiackovwiki kiacKows K VoorHoof...
Karol Gackouuss kiackckoskkıklcıok k. Uoorhaßs...
Joe Houwe liog Cin Jppp hu P #Pp9  Jop Loan Aa...
```

Het model herhaalde de invoertekst 2 tot 5 keer per regel en verminkte de herhalingen. De gemiddelde OCR CER was 1.378, dus slechter dan willekeurig.

## Oorzaak

Twee feiten over hoe DiffBrush getraind is, te vinden in [generate.py](DiffBrush/generate.py) en [DiffBrush/data_loader/base_dataset.py](DiffBrush/data_loader/base_dataset.py):

1. **De training input lengte was 35 tot 61 karakters** (zie de `if 35 <= len(text) <= 61` filter in [generate.py:65](DiffBrush/generate.py#L65)). Deze lange regels vulden de volledige 1024 pixel brede output canvas.
2. **Korte regels werden getiled door de `concat_short_img` augmentatie** ([base_dataset.py:109](DiffBrush/data_loader/base_dataset.py#L109)): zowel de afbeelding als de transcript werden 2 tot 5 keer herhaald zodat het resultaat alsnog 1024 pixels vulde.

Als we het model een Nederlandse adresregel zoals `"Voorhofstraat 12"` (16 karakters) voeren, dan zit het in het regime van "korte content + vul het canvas". Maar onze content tensor bevat maar 16 tokens, terwijl de training data voor dat regime **getilede** content had (dezelfde tekst meerdere keren herhaald). De cross-attention verspreidt 16 tokens over 1024 pixels canvas en raakt daarbij gedrag dat het tijdens de tile-augmentatie training heeft geleerd, namelijk tekst herhalen.

De hallucinaties zijn het model dat probeert te doen wat de training hem geleerd heeft, alleen met de verkeerde input.

## De fix

Twee aanpassingen in de notebook:

### 1. Tile de content expliciet ([cel 5](diffbrush_eval.ipynb))

Voor de generatie herhalen we de tekst met enkele spaties als scheiding tot de totale lengte `≥ 45` karakters is (midden van de training range). Zo zit de content precies in distributie.

```python
def _tile_text(text: str, target_len: int = 45) -> tuple[str, int]:
    if len(text) >= target_len:
        return text, 1
    n_tiles = max(1, math.ceil((target_len + 1) / (len(text) + 1)))
    tiled = (text + ' ') * (n_tiles - 1) + text
    return tiled, n_tiles
```

Voor `"Voorhofstraat 12"` (16 karakters) krijgen we de getilede string `"Voorhofstraat 12 Voorhofstraat 12 Voorhofstraat 12"` (50 karakters, 3 tiles).

Het model produceert nu **schone** herhaalde tekst zonder verminking, omdat we precies in het regime zitten waarop het getraind is.

### 2. Crop de eerste tile op basis van proportionele breedte ([cel 6](diffbrush_eval.ipynb))

De cross-attention van DiffBrush verspreidt getilede content gelijkmatig over de 1024 pixel canvas. De eerste tile beslaat dus ongeveer:

```
right_cap = 1024 * text_length / tiled_length + 4
```

De `+4` is een kleine veiligheidsmarge om de laatste karakters niet af te kappen (puntje van een `i`, staart van een `g`), zonder dat de eerste letter van de volgende tile in de crop terechtkomt.

Voor `"Voorhofstraat 12"`: `1024 * 16 / 50 + 4 = 332 pixels`. De eerste tile wordt gecropt op kolom 332 van de 1024 pixel brede ruwe output.

## Hoe de iteratie verliep

Een aantal tussentijdse pogingen voordat we bij tiling uitkwamen:

| Poging | Idee | Wat mis ging |
|---|---|---|
| Origineel | Geen padding, crop op basis van gaps | Compleet onzin met herhalingen |
| 1 | Pad content met PAD-token glyphs (nul matrix) | Echo's aan het eind zoals `"12 12"`, `"DEN DEN"` |
| 2 | Strakkere rechterrand cap via `max_px_per_char` | Tekst werd halverwege afgekapt in cursive (bijvoorbeeld `Gackowski → Gackaw`) |
| 3 | Pad met spaties in plaats van PAD tokens | Echo's lekken nog steeds door binnen de tekstregio |
| 4 | Tile content + crop op `tile_px + 24` marge | Schone tiles, maar eerste karakters van de volgende tile lekken |
| **5 (definitief)** | **Tile content + proportionele crop + 4 px marge** | **Werkt** |

De grote sprong was van poging 4 naar 5: het besef dat DiffBrush content tokens gelijkmatig verspreidt, waardoor de pixel breedte van de eerste tile uitrekenbaar is op basis van de tile structuur in plaats van te raden via `max_px_per_char`.

## Aangepaste bestanden

Alleen [diffbrush_eval.ipynb](diffbrush_eval.ipynb):

- **Cel 5**: `_tile_text` toegevoegd en `text_to_content` herschreven zodat die `(tensor, n_tiles, tiled_len)` teruggeeft in plaats van alleen de tensor.
- **Cel 6**: `crop_to_first_line` (die probeerde gaps in de getilede output te detecteren) vervangen door `crop_first_tile` (die de tile structuur exact kent). Er is ook een in-memory cache toegevoegd van de ruwe 1024 pixel brede generaties, zodat cropping bijgesteld kan worden zonder dat diffusion opnieuw hoeft te draaien.

Er zijn geen aanpassingen gedaan aan de DiffBrush source code. Alles staat in de notebook.

## Wat nog niet perfect is

Deze punten zijn inherent aan het model, niet aan de cropping:

- **Karakter substituties**: `Gackowski → Gachowski`, `Palmestraat → Pallmestrat`, `2616 → 2016`. DiffBrush heeft alleen IAM Engels handschrift gezien tijdens training, dus Nederlandse straatnamen en buitenlandse namen zijn out-of-distribution op contentniveau.
- **Kleine 1 of 2 karakter lekjes in cursive (writer 634)**: het model comprimeert tiles iets dichter op elkaar in cursive stijlen, dus de eerste letter van de volgende tile kan 1 of 2 px binnen onze proportionele crop landen.
- **Af en toe vallen er letters weg**: het model schrijft soms 15 karakters terwijl er 16 gevraagd zijn (bijvoorbeeld `VOORHOFSTRAT` in plaats van `VOORHOFSTRAAT`).

Om deze problemen op te lossen moeten we DiffBrush fine-tunen op Prime Vision data (duur), of zorgvuldiger met style references werken. Zie de "Vervolgstappen" markdown cell onderaan de notebook voor het gedocumenteerde plan.
