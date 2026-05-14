# Fase 2 presentatieplan, Prime Vision

Korte gids voor wat je laat zien en hoe je het laat zien. Gebaseerd op de rubric en de inhoud die je nu hebt.

---

## Verhaallijn in één zin

We hebben twee handschriftgeneratie modellen (DiffBrush en DiffusionPen) werkend gekregen op Nederlandse adresregels, twee modelspecifieke generatie problemen gediagnostiseerd en opgelost, en de output kwantitatief (OCR CER/WER) en kwalitatief (visueel) vergeleken. Dat geeft ons een onderbouwde keuze voor welk model we in fase 3 gaan fine-tunen op Prime Vision data.

---

## Tijdverdeling (15 minuten totaal)

| Onderdeel | Tijd | Wie |
|---|---|---|
| Inleiding en context | 2 min | Spreker A |
| Onderzoeksaanpak en DSLC koppeling | 2 min | Spreker A |
| Model 1: DiffBrush | 3 min | Spreker B |
| Model 2: DiffusionPen | 3 min | Spreker A |
| Vergelijking en interpretatie | 3 min | Spreker B |
| Reflectie en vooruitblik fase 3 | 2 min | beiden |

Wisselen na de helft houdt het levendig en zorgt dat iedereen aan bod komt.

---

## Slide overzicht

### Slide 1, Titel
- Project: synthetisch handschrift genereren voor OCR training
- Studenten + Prime Vision begeleider + datum

### Slide 2, Probleem en doel
- Prime Vision heeft te weinig training data voor moeilijk handschrift (connected, overlap, dunne strokes, lange ascenders/descenders)
- Doel fase 2: twee generatieve modellen werkend krijgen op Nederlandse adresregels en hun kwaliteit kwantitatief evalueren

### Slide 3, Onderzoeksvragen
- Welk model genereert de meest realistische Nederlandse adresregels?
- Hoe meten we generatiekwaliteit zonder downstream training?
- Welke imperfecties produceren de modellen, en zijn die bruikbaar of probleem?

### Slide 4, Aanpak en DSLC koppeling
- CRISP-DM fases waar we in zitten: Data Understanding en Modeling
- Iteraties: model laden → genereren → diagnose → fix → opnieuw evalueren
- Twee concrete iteratieslagen documenteren we (hallucination fixes, zie volgende slides)

### Slide 5, DiffBrush, hoe het werkt
- Regel-gebaseerd, één 64×1024 image per regel
- Style komt van echte handgeschreven sample
- Content via 16×16 unifont glyph stack

### Slide 6, DiffBrush, het tile probleem
- Korte tekst (`"Den Haag"`) leidde tot hallucinaties zoals `"DEN DEN DEN"` of `"GACKOWKKK"`
- Oorzaak: training gebruikte tile-augmentatie waarbij korte tekst werd herhaald om het 1024 px canvas te vullen
- Fix: zelf tilen tot 45 karakters, en daarna de eerste tile proportioneel croppen
- **Dit is een Data Science Life Cycle iteratie die je expliciet benoemt**

### Slide 7, DiffusionPen, hoe het werkt
- Woord-gebaseerd, 64×256 per woord
- Stitching met min-blend en baseline jitter om naden te verbergen
- Style via writer label (339 IAM writers)

### Slide 8, DiffusionPen, het digit probleem
- Postcodes zoals `"2511"` werden gerenderd als `"2 5 1 1"` met letter-spacing tussen elk cijfer
- Oorzaak: IAM training data bevat nauwelijks multi-digit sequenties
- Fix: cijfers los genereren en stitchen op 2 px gap
- **Tweede DSLC iteratie**

### Slide 9, Evaluatie methode
- 5 Nederlandse adressen × 3 IAM writers = 15 blokken per model
- Metric 1: visuele inspectie (grid + side-by-side met echte Prime Vision samples)
- Metric 2: OCR readback met EasyOCR, CER en WER tegen de bedoelde tekst
- Beperking: EasyOCR is getraind op gedrukte tekst, niet cursive. CER overdrijft fouten op cursive cijfers (1 → /, 5 → S)

### Slide 10, Resultaten visueel
- Toon het grid van DiffBrush (5 rijen, 3 kolommen)
- Toon het grid van DiffusionPen (5 rijen, 3 kolommen)
- Toon één side-by-side strip tegen een echt Prime Vision sample

### Slide 11, Resultaten kwantitatief
- Tabel met gemiddelde CER en WER per model (uit de vergelijkings cel in de notebook)
- Per-adres CER tabel, zodat je laat zien dat sommige adressen voor beide modellen lastig zijn (lange Nederlandse straatnamen)

### Slide 12, Wat werkt en wat niet
**Werkt**
- Beide modellen produceren leesbare Nederlandse output
- Stijl variatie tussen writers is duidelijk zichtbaar
- Cijfers en hoofdletters worden correct geplaatst

**Werkt niet (nog)**
- Lange Nederlandse samenstellingen (Voorhofstraat, Meerdervoort) worden licht verminkt: OOD karakter sequenties voor IAM
- DiffusionPen mist connected handwriting tussen woorden door de woord-voor-woord aanpak
- Korte tokens (BV, LR) worden soms verkeerd gerenderd

### Slide 13, Reflectie
- Wat verraste ons: dat een trainings-augmentatie zoals tiling zo'n drastisch effect heeft op inference gedrag bij OOD input
- Wat hebben we geleerd: model gedrag bij OOD input is voorspelbaar als je de training pipeline begrijpt
- Wat hadden we anders kunnen doen: eerder visueel kijken naar de output in plaats van direct OCR cijfers vergelijken (OCR maskeert sommige fixes)

### Slide 14, Doorvertaling naar eindproduct
- Welk model: nog open. Visueel lijkt DiffBrush meer connected handwriting te geven (regel niveau), DiffusionPen heeft meer style variatie (per writer label). Vergelijk de cijfers en kies dan.
- Volgende stap (fase 3): fine-tunen op Prime Vision data en een HTR/OCR model trainen op synthetisch-only / real-only / mixed om de echte downstream CER te meten

### Slide 15, Vragen

---

## Rubric check, doe dit voor je presenteert

| Criterium | Hoe je dat afdekt |
|---|---|
| Inhoudelijke voortgang | Slide 6, 8, 10, 11 (twee fixes + resultaten) |
| Onderzoeksmatige aanpak | Slide 3, 4, 9 (onderzoeksvragen, DSLC, evaluatie methode) |
| Data Science Life Cycle | Slide 4 expliciet noemen, slides 6 en 8 als concrete iteraties laten zien |
| Onderbouwing keuzes | Slide 9 (waarom CER + visueel), slide 12 (waarom deze imperfecties acceptabel zijn) |
| Resultaten en interpretatie | Slide 10, 11, 12 (cijfers + waarom CER cursive cijfers oneerlijk straft) |
| Reflectie | Slide 13 |
| Doorvertaling eindproduct | Slide 14 |
| Structuur | Heldere inleiding-kern-slot, deze indeling volgt dat |
| Presentatievorm | Korte bullets, geen volzinnen op slides, mondeling toelichten |
| Tijd en taakverdeling | 15 minuten, beide sprekers aan bod (zie tabel boven) |

---

## To-do's voor je presenteert

1. **DiffBrush notebook helemaal doorlopen** om `ocr_results_diffbrush.json` te produceren. De OCR cel slaat de resultaten nu automatisch op.
2. **DiffusionPen notebook idem** voor `ocr_results_diffusionpen.json`.
3. **Vergelijkings cel runnen** (cel 13 in DiffBrush notebook). Output kopieer je in slide 11.
4. **Screenshots maken** van:
   - Het grid van cel 10 in beide notebooks (voor slide 10)
   - Het side-by-side van cel 12 in beide notebooks (voor slide 10)
   - De vergelijkings tabel (voor slide 11)
5. **Korte tekst per slide schrijven** in spreker notities. Niet voorlezen op slides.
6. **Dry-run van 15 minuten** met timer, één keer.

---

## Antwoorden op verwachte vragen

**Waarom niet meteen fine-tunen?**
We wilden eerst weten of de modellen overhaupt werkbare output produceren voor Nederlands. Anders fine-tune je iets dat sowieso niet goed schaalt naar onze use case.

**Waarom IAM en niet Nederlandse data?**
Beide modellen zijn alleen op IAM (Engels) of WikiText getraind beschikbaar. Eigen Nederlandse data trainen kost weken en valt onder fase 3.

**Waarom CER en niet iets fancier zoals FID?**
CER is direct gerelateerd aan de downstream taak van Prime Vision (OCR op enveloppen). FID is een algemene image-quality metric die niet zegt of een mens de tekst kan lezen.

**Waarom 5 adressen en niet 100?**
Genereren kost ~5 minuten per blok op CPU, ~30 seconden op GPU. 15 blokken per model gaf genoeg signaal om de problemen te diagnostiseren. In fase 3 schaalt dit op naar honderden samples voor downstream training.

**Wat als beide modellen ongeveer gelijk scoren?**
Dan kijken we naar imperfecties die voor Prime Vision waardevol zijn: connected handwriting, overlap, dunne strokes. DiffBrush wint op het eerste (regel niveau), DiffusionPen geeft meer style variatie. We zouden ook beide kunnen combineren in fase 3.
