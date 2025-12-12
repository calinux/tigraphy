# Instrucțiuni de Testare OCR Îmbunătățit

## Diferențe cheie față de versiunea originală

### 1. **OCR_THRESH este acum folosit corect**
- `0` = fără threshold (Tesseract decide singur)
- `> 0` = binary threshold cu valoarea specificată (ex: 180)
- `-1` = Otsu automatic threshold

### 2. **OCR_PREPROCESS nou** - selectează metoda de preprocesare:
- `minimal` - doar upscale, fără filtre (pentru screenshots curate)
- `standard` - upscale + optional threshold
- `code` - optimizat pentru cod (CLAHE contrast, fără blur)
- `noisy` - denoise + adaptive threshold (pentru imagini de calitate slabă)

### 3. **OCR_LANG corect**
- Folosește valori valide: `eng`, `ron`, `lat`, etc.
- NU mai folosește `script/Latin` care era invalid

### 4. **Debug mode** (`OCR_DEBUG=1`)
- Salvează imaginile preprocesate pentru a vedea ce primește Tesseract
- Util pentru a ajusta parametrii

---

## Testare rapidă

### Test 1: Modul cod/technical (pentru imaginea .sln)

```bash
# Copiază imaginea .sln în clipboard, apoi:
./start_ocr_improved.command
# Selectează opțiunea 1 (Code/Technical)
```

### Test 2: Direct pe un fișier imagine

```bash
# Setează variabilele manual:
export OCR_LANG="eng"
export OCR_PSM="6"
export OCR_PREPROCESS="code"
export OCR_UPSCALE="2.0"
export OCR_THRESH="0"
export OCR_DEBUG="1"

# Rulează pe imagine:
source /Users/calinux/.venvs/ocr/bin/activate
python clipboard_ocr_improved.py /path/to/image.png
```

### Test 3: Comparație între metode

```bash
# Test cu preprocessing minimal:
export OCR_PREPROCESS="minimal"
python clipboard_ocr_improved.py test.png

# Test cu preprocessing code:
export OCR_PREPROCESS="code"
python clipboard_ocr_improved.py test.png

# Test cu preprocessing noisy:
export OCR_PREPROCESS="noisy"
python clipboard_ocr_improved.py test.png
```

---

## Pentru imaginea .sln (Visual Studio Solution)

Setări recomandate:
```bash
export OCR_LANG="eng"
export OCR_PSM="6"          # Bloc uniform de text
export OCR_PREPROCESS="code"  # Păstrează detaliile fine
export OCR_UPSCALE="2.0"
export OCR_THRESH="0"       # Lasă Tesseract să decidă
export OCR_LAYOUT="grid"    # Păstrează spațierea
```

Acest tip de imagine (screenshot de cod cu fundal alb, text negru) NU are nevoie de:
- Denoise (nu e zgomot)
- Adaptive threshold (contrastul e deja bun)
- Blur (ar distruge caracterele mici)

---

## Debugging

Dacă rezultatele sunt proaste:

1. **Activează debug**: `export OCR_DEBUG=1`
2. **Verifică imaginea preprocesată** în `ocr_output/*_debug.png`
3. Dacă textul e ilizibil în debug image → preprocessing-ul e prea agresiv
4. Încearcă `OCR_PREPROCESS="minimal"`

---

## Verificare Tesseract

```bash
# Vezi limbile instalate:
tesseract --list-langs

# Test manual:
tesseract test.png output --oem 3 --psm 6 -l eng

# Vezi rezultatul:
cat output.txt
```
