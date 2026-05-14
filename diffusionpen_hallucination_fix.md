# DiffusionPen digit-spacing fix

Notities over het werk dat is gedaan om te voorkomen dat [diffusionpen_eval.ipynb](diffusionpen_eval.ipynb) adres tokens met meerdere cijfers (postcodes, huisnummers) op letterniveau spaceert, waardoor OCR ze als losse woorden leest.

---

## Het probleem

Gegenereerde adresblokken zagen er zo uit:

```
Karol Gackowski
Vonluogttract  , 2          ← "12" gesplitst naar ", 2"
2 5 1  A B J e n  H a o g   ← "2511" naar "2 5 1 1" met gaten
```

Specifieke fouten die we visueel waarnamen:

| Token | Werd gegenereerd als | Probleem |
|---|---|---|
| `"12"` | `", 2"` of `"1 2"` | gat tussen cijfers en "1" naar "," |
| `"27"` | `"2 7"` | ~15 px gat tussen de cijfers |
| `"81"` | `"8 1"` | hetzelfde |
| `"2511"` | `"251"` of verminkt | letters weggevallen of vervangen |
| `"1011"` | `"10. 1"` | gehallucineerde punt |
| `"2616"` | `"2GG"` | cijfer naar letter substitutie |
| `"14"` | `"11"` | verkeerd cijfer |

Het model herhaalde de tekst niet zoals DiffBrush deed. DiffusionPen werkt op woordniveau en genereert één woord per keer. De fout zit hier puur in hoe sequenties van meerdere cijfers gerenderd worden.

---

## Oorzaak

DiffusionPen gebruikt een CANINE character-level transformer als text encoder
(`google/canine-c`). Bij inference wordt de tokenizer aangeroepen met `max_length=40`:

```python
# train.py, Diffusion.sampling(), line 264
text_features = tokenizer(text_features, padding="max_length", truncation=True,
                          return_tensors="pt", max_length=40).to(args.device)
```

Dit is consistent met de training (ook `max_length=40` in de training loop). Er zit dus geen tokenizer mismatch.

Het echte probleem zit in de **training corpus**. DiffusionPen is getraind op de IAM Handwriting Database, die bestaat uit handgeschreven Engelse tekst uit het Lancaster-Oslo/Bergen corpus: boeken, artikelen en brieven. IAM bevat nauwelijks sequenties van meerdere cijfers. De karakter verdeling is overwegend alfabetisch. Losse "1", "2", tot en met "9" komen voor als geïsoleerde glyphs (Romeinse cijfers, voetnoot markers), maar "2511" of "27" als doorlopende sequentie komt vrijwel nooit voor.

Wanneer het model geconditioneerd wordt op `"27"` geeft de CANINE encoder aparte embeddings voor `'2'` (U+0032) en `'7'` (U+0037). De cross-attention van de UNet heeft tijdens IAM training geleerd om elke glyph embedding te behandelen als een aparte *letter*, en letters binnen een woord worden gerenderd met letter-level spacing (~15 px op de 64x256 canvas). Het resultaat is `"2 7"` in plaats van `"27"`.

Voor langere sequenties zoals `"2511"` substitueert het model bovendien visueel vergelijkbare karakters: `'5' → 'G'`, `'1' → 'I'`, en dergelijke, omdat de karakter sequentie `2511` geen training signaal heeft.

Dit is het DiffusionPen equivalent van het DiffBrush tile probleem (zie [diffbrush_hallucination_fix.md](diffbrush_hallucination_fix.md)). In beide gevallen genereert het model wat de training hem geleerd heeft voor het gegeven input regime. Het regime van DiffBrush was "korte tekst, tile en vul canvas". Bij DiffusionPen is het regime "opeenvolgende karakters, behandel elk als losse letter met standaard spacing".

---

## De fix

**Eén aanpassing in de notebook**: voeg `_render_token` toe in cel 8 (layout cel) en roep deze aan vanuit `render_line`.

### Logica

Voor tokens die puur numeriek zijn (`token.isdigit() and len(token) > 1`), genereer elk cijfer afzonderlijk en stitch ze met een 2 px gap:

```python
DIGIT_GAP = 2  # tight gap (px) between digits within a number token

def _render_token(token: str, writer_id: int) -> np.ndarray:
    if token.isdigit() and len(token) > 1:
        imgs = [_clean_bg(np.array(generate_word(d, writer_id))) for d in token]
        h = max(im.shape[0] for im in imgs)
        total_w = sum(im.shape[1] for im in imgs) + DIGIT_GAP * (len(imgs) - 1)
        canvas = np.full((h, max(1, total_w)), BG, dtype=np.uint8)
        x = 0
        for im in imgs:
            _blend_paste(canvas, im, x, 0)
            x += im.shape[1] + DIGIT_GAP
        return canvas
    return _clean_bg(np.array(generate_word(token, writer_id)))
```

**Waarom werkt dit**: losse cijfer karakters (`'2'`, `'5'`, `'1'`) komen WEL voor als standalone karakters in IAM (Romeinse cijfers, hoofdstuknummers, voetnoten). Het model kan een losse `'2'` schoon renderen. Door elk cijfer als losstaand woord te genereren en te stitchen met een 2 px gap blijven we volledig in distributie. De 2 px gap is strak genoeg om als cijfer sequentie gelezen te worden, en de letter spacing (15 tot 22 px) is volledig verdwenen.

### Toegevoegd: raw-output cache (cel 6)

De diffusion run is de bottleneck, ongeveer 3 tot 5 minuten voor alle 15 blokken. Er is een `_word_cache` dict toegevoegd aan `generate_word`:

```python
_word_cache: dict = {}  # (word, writer_id) -> raw PIL Image before width_crop

@torch.no_grad()
def generate_word(word: str, writer_id: int, crop: bool = True) -> Image.Image:
    key = (word, writer_id)
    if key not in _word_cache:
        # ... run diffusion, store result ...
        _word_cache[key] = raw_image
    img = _word_cache[key]
    if crop:
        img = width_crop(img)
    return img
```

Met cijfer-voor-cijfer generatie worden unieke losse cijfers (bijvoorbeeld `'1'` voor writer 12) één keer gegenereerd en hergebruikt over alle adressen die dat cijfer bevatten. Zo blijft het totale aantal diffusion calls ongeveer gelijk aan het origineel, ondanks dat postcodes nu in 4 calls gesplitst worden.

Cel 6 opnieuw runnen wist de cache. `_word_cache.clear()` wist de cache handmatig zonder dat de rest van de model state gereset wordt.

---

## Resultaten

Visuele inspectie van alle 15 gegenereerde blokken bevestigde:

| Token | Voor | Na |
|---|---|---|
| `"12"` | `", 2"` | `"12"` ✓ |
| `"27"` | `"2 7"` | `"27"` ✓ |
| `"81"` | `"8 1"` | `"81"` ✓ |
| `"14"` | `"11"` | `"14"` ✓ |
| `"2511"` | `"251"` (verminkt) | `"2511"` ✓ |
| `"2517"` | `"254 A5"` | `"2517"` ✓ |
| `"3032"` | `"3032"` (was al OK) | `"3032"` ✓ |
| `"2616"` | `"2GG"` | `"2616"` ✓ |
| `"1011"` | `"10. 1"` | `"1011"` ✓ |

---

## OCR CER kanttekening

EasyOCR runnen op de nieuwe output gaf een *hogere* gemiddelde CER (0.394) dan de oude output (0.355). Dat is misleidend om twee redenen:

1. **Cursive cijfer rendering**: EasyOCR leest een cursive IAM-style `'1'` als `'/'` en `'5'` als `'S'`. Dit zijn handschrift stijl artefacten, geen generatie fouten. Een menselijke lezer en een cursive-getraind HTR model zouden ze correct herkennen. De CER metric straft ze even zwaar af als echte generatie fouten.

2. **Verstoorde randomness**: door losse cijfers te genereren verandert de volgorde waarin `torch.randn` ruis gebruikt wordt, dus alle volgende woorden in dezelfde generatie run komen uit een andere random state. De vergelijking is dus een andere random draw, geen gecontroleerde A/B.

**Visuele inspectie is het betrouwbaardere signaal voor deze fix.** Voor een downstream HTR evaluatie kun je beter een model gebruiken dat getraind is op cursive handschrift (bijvoorbeeld een TrOCR die fine-tuned is op IAM) in plaats van EasyOCR.

---

## Wat nog niet perfect is (inherent aan het model)

Deze punten zijn intrinsiek aan DiffusionPen omdat het getraind is op IAM Engelse woorden. Ze kunnen niet in de notebook opgelost worden:

- **Lange Nederlandse samenstellingen**: `"Voorhofstraat"` → `"Vorhoogstraet"`, `"Kerkstraat"` → licht verminkt. Sequenties van 10+ karakters komen weinig voor in IAM woorden en het model comprimeert ze met karakter substituties. `"Rotterdam"` (9 karakters) en `"Kerkstraat"` (10 karakters) zitten op de grens, soms gaat het goed.
- **Korte all-cap tokens**: `"BV"` → `"3V"`, `"LR"` → `"R"`, `"Olof"` → `"Oof"`. Het model laat soms letters vallen of substitueert ze in hele korte tokens, vooral met hoofdletters.
- **Style-scale inconsistentie**: korte woorden zoals `"Haag"` (4 karakters) en `"Berg"` (4 karakters) worden visueel kleiner gerenderd dan langere woorden op dezelfde regel. Dat komt omdat het model glyph breedte proportioneel verdeelt op basis van het aantal karakters over de 256 px canvas. Een kort woord krijgt minder canvas, dus de strokes lijken kleiner wanneer ze opgeschaald worden voor weergave.
- **Cursive cijfer uiterlijk**: losse cijfers zien er correct uit voor een mens, maar OCR tools die getraind zijn op gedrukte tekst lezen `'1'` als `'/'`, `'5'` als `'S'`, en zo verder.

---

## Aangepaste bestanden

Alleen [diffusionpen_eval.ipynb](diffusionpen_eval.ipynb):

- **Cel 6** (`generate_word`): `_word_cache` dict toegevoegd en caching logica in `generate_word`.
- **Cel 8** (layout): `DIGIT_GAP = 2` toegevoegd, `_render_token` functie toegevoegd, `render_line` aangepast zodat die `_render_token` aanroept in plaats van direct `generate_word`.

Geen aanpassingen aan de DiffusionPen source code.

---

## Vergelijking: DiffBrush vs DiffusionPen failure modes

Beide modellen falen om dezelfde onderliggende reden, namelijk OOD input ten opzichte van de training distributie. Maar de vorm van falen verschilt:

| | DiffBrush | DiffusionPen |
|---|---|---|
| Type model | Regel niveau (volledige adresregel) | Woord niveau (één woord per 64x256 afbeelding) |
| Training OOD input | Korte tekst (< 35 karakters) | Sequenties van meerdere cijfers |
| Failure mode | Tekst 2 tot 5 keer herhaald over canvas | Letter spacing tussen cijfers |
| Fix strategie | Tile input om canvas te vullen, crop eerste tile | Genereer elk cijfer apart, stitch op 2 px |
| Resterende issues | Nederlandse karakter substituties, cursive tile-edge lek | Nederlandse samenstellingen verminking, OCR leest cursive `'1'` als `/` |
