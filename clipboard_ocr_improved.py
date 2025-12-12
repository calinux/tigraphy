#!/usr/bin/env python3
"""
Improved Clipboard OCR for macOS
Fixes:
- OCR_THRESH is now actually used
- Less aggressive preprocessing for clean screenshots
- Multiple preprocessing profiles
- Better handling of code/technical content
"""
import os
import re
import csv
import io
import time
import hashlib
import statistics
from datetime import datetime
from typing import Optional, Tuple, List, Dict

import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import pytesseract

# --- macOS pasteboard via PyObjC ---
try:
    from AppKit import (
        NSPasteboard,
        NSPasteboardTypePNG,
        NSPasteboardTypeTIFF,
        NSPasteboardTypePDF,
        NSPasteboardTypeFileURL,
        NSPasteboardTypeString,
    )
    from Foundation import NSData, NSURL
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False
    print("[Warning] PyObjC not available - clipboard watching disabled")

COMMON_TESS_PATHS = [
    "/opt/homebrew/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/usr/bin/tesseract",
]


def ensure_tesseract_path():
    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd and os.path.isfile(env_cmd):
        pytesseract.pytesseract.tesseract_cmd = env_cmd
        return
    for p in COMMON_TESS_PATHS:
        if os.path.isfile(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def nsdata_to_bytes(nsdata) -> bytes:
    return bytes(nsdata)


def load_pil_from_nsdata(nsdata) -> Image.Image:
    raw = nsdata_to_bytes(nsdata)
    return Image.open(BytesIO(raw))


def read_image_from_file_url_data(nsdata) -> Optional[Tuple[Image.Image, str]]:
    try:
        text = nsdata_to_bytes(nsdata).decode("utf-8").strip()
        for line in text.splitlines():
            url = NSURL.URLWithString_(line.strip())
            if not url or not url.isFileURL():
                continue
            path = url.path()
            if path.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")):
                try:
                    img = Image.open(path)
                    return img, f"file:{path}"
                except Exception:
                    continue
    except Exception:
        pass
    return None


def grab_pasteboard_image(pb):
    for t in (NSPasteboardTypePNG, NSPasteboardTypeTIFF, NSPasteboardTypePDF):
        data = pb.dataForType_(t)
        if data:
            try:
                img = load_pil_from_nsdata(data)
                raw = nsdata_to_bytes(data)
                fmt = "png" if t == NSPasteboardTypePNG else ("tiff" if t == NSPasteboardTypeTIFF else "pdf")
                return img, f"pasteboard:{fmt}", raw
            except Exception:
                pass

    filedata = pb.dataForType_(NSPasteboardTypeFileURL)
    if filedata:
        result = read_image_from_file_url_data(filedata)
        if result:
            img, desc = result
            b = BytesIO()
            img.save(b, format="PNG")
            return img, desc, b.getvalue()

    return None


def get_pasteboard_text(pb) -> Optional[str]:
    data = pb.dataForType_(NSPasteboardTypeString)
    if not data:
        return None
    try:
        return nsdata_to_bytes(data).decode("utf-8", errors="replace")
    except Exception:
        return None


def sanitize_seed(s: str, limit: int = 20) -> str:
    s = re.sub(r"[^\w\-\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    seed = s[:limit].strip()
    return seed if seed else "ocr"


# ==================== IMPROVED PREPROCESSING ====================

def preprocess_minimal(img: Image.Image) -> Image.Image:
    """
    Minimal preprocessing - for clean screenshots with good contrast.
    Only upscales, no thresholding or filters.
    """
    open_cv_image = np.array(img.convert('RGB'))[:, :, ::-1].copy()
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)

    upscale = float(os.environ.get("OCR_UPSCALE", "1.5"))
    if upscale > 1.0:
        gray = cv2.resize(gray, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_LANCZOS4)

    return Image.fromarray(gray)


def preprocess_standard(img: Image.Image) -> Image.Image:
    """
    Standard preprocessing - upscale + optional threshold.
    Uses OCR_THRESH environment variable.
    """
    open_cv_image = np.array(img.convert('RGB'))[:, :, ::-1].copy()
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)

    # 1. Upscale
    upscale = float(os.environ.get("OCR_UPSCALE", "1.5"))
    if upscale > 1.0:
        gray = cv2.resize(gray, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_LANCZOS4)

    # 2. Threshold - ONLY if OCR_THRESH > 0
    thresh_val = int(os.environ.get("OCR_THRESH", "0"))
    if thresh_val > 0:
        # Simple binary threshold
        _, gray = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
    elif thresh_val == -1:
        # Otsu automatic threshold
        _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # else: no thresholding (thresh_val == 0)

    return Image.fromarray(gray)


def preprocess_noisy(img: Image.Image) -> Image.Image:
    """
    For noisy/low-quality images - denoising + adaptive threshold.
    """
    open_cv_image = np.array(img.convert('RGB'))[:, :, ::-1].copy()
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)

    # 1. Upscale
    upscale = float(os.environ.get("OCR_UPSCALE", "2.0"))
    if upscale > 1.0:
        gray = cv2.resize(gray, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)

    # 2. Denoise
    gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # 3. Adaptive threshold for uneven lighting
    gray = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
        blockSize=31, C=2
    )

    return Image.fromarray(gray)


def preprocess_code(img: Image.Image) -> Image.Image:
    """
    Optimized for code/technical content - preserves fine details.
    NO blur, NO aggressive thresholding.
    """
    open_cv_image = np.array(img.convert('RGB'))[:, :, ::-1].copy()
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)

    # 1. Upscale with high-quality interpolation
    upscale = float(os.environ.get("OCR_UPSCALE", "2.0"))
    if upscale > 1.0:
        gray = cv2.resize(gray, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_LANCZOS4)

    # 2. Contrast enhancement (CLAHE) - subtle
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # 3. Optional light sharpening for text edges
    sharpen = os.environ.get("OCR_SHARPEN", "0")
    if sharpen == "1":
        kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
        gray = cv2.filter2D(gray, -1, kernel)
        gray = np.clip(gray, 0, 255).astype(np.uint8)

    return Image.fromarray(gray)


def preprocess(img: Image.Image) -> Image.Image:
    """
    Main preprocessing dispatcher - selects method based on OCR_PREPROCESS env var.
    """
    method = os.environ.get("OCR_PREPROCESS", "standard").lower()

    if method == "minimal":
        return preprocess_minimal(img)
    elif method == "noisy":
        return preprocess_noisy(img)
    elif method == "code":
        return preprocess_code(img)
    else:  # "standard" or default
        return preprocess_standard(img)


# ==================== OCR CONFIG ====================

def tess_config() -> str:
    oem = os.environ.get("OCR_OEM", "3")
    psm = os.environ.get("OCR_PSM", "6")
    dpi = os.environ.get("OCR_DPI", "300")
    preserve_spaces = os.environ.get("OCR_PRESERVE_SPACES", "1")

    config = f'--oem {oem} --psm {psm} -c user_defined_dpi={dpi} -c preserve_interword_spaces={preserve_spaces}'

    # Character whitelist - restricts recognition to specific characters
    # Useful for tokens, hex, API keys where you know the character set
    whitelist = os.environ.get("OCR_WHITELIST", "")
    if whitelist:
        # Escape special chars for tesseract config
        config += f' -c tessedit_char_whitelist={whitelist}'

    # Additional tesseract config options
    extra = os.environ.get("OCR_EXTRA_CONFIG", "")
    if extra:
        config += f' {extra}'

    return config


def ocr_text(img: Image.Image, lang: str) -> str:
    processed = preprocess(img)
    return pytesseract.image_to_string(processed, lang=lang, config=tess_config())


def ocr_tsv(img: Image.Image, lang: str) -> str:
    processed = preprocess(img)
    return pytesseract.image_to_data(processed, lang=lang, config=tess_config(), output_type=pytesseract.Output.STRING)


# ==================== TSV TO GRID ====================

def grid_from_tsv(tsv_str: str) -> str:
    """Render words to a monospaced grid using TSV word boxes."""
    reader = csv.DictReader(io.StringIO(tsv_str), delimiter='\t')
    words = []
    for r in reader:
        text = r.get('text', '').strip()
        conf = r.get('conf', '-1')
        if text and conf:
            try:
                if int(float(conf)) >= 0:  # Only include confident detections
                    words.append(r)
            except ValueError:
                pass

    if not words:
        return ''

    # Group by block->par->line
    grouped: Dict[Tuple[str, str, str], List[dict]] = {}
    for w in words:
        key = (w.get('block_num', '0'), w.get('par_num', '0'), w.get('line_num', '0'))
        grouped.setdefault(key, []).append(w)

    lines_out: List[str] = []
    for key in sorted(grouped, key=lambda k: tuple(map(int, k))):
        line_words = grouped[key]
        line_words.sort(key=lambda w: int(w.get('left', '0')))

        # Estimate average char width
        widths = []
        for w in line_words:
            try:
                tw = len(w['text'])
                bw = int(w['width'])
                if tw > 0 and bw > 0:
                    widths.append(bw / tw)
            except (KeyError, ValueError):
                pass

        cell = statistics.median(widths) if widths else 8.0
        cell = max(4.0, min(cell, 24.0))

        # Build row buffer
        max_right = 0
        try:
            max_right = max(int(w['left']) + int(w['width']) for w in line_words)
        except (KeyError, ValueError):
            max_right = 2000

        cols = int(max_right / cell) + 10
        row = [' '] * cols

        for w in line_words:
            try:
                left = int(w['left'])
                start_col = int(left / cell)
                text = w['text']
                end_needed = start_col + len(text) + 1
                if end_needed > len(row):
                    row.extend([' '] * (end_needed - len(row)))
                for i, ch in enumerate(text):
                    pos = start_col + i
                    row[pos] = ch
            except (KeyError, ValueError):
                continue

        lines_out.append(''.join(row).rstrip())

    return '\n'.join(lines_out)


# ==================== OUTPUT ====================

def build_filename(seed: Optional[str]) -> str:
    now = datetime.now()
    if seed:
        clock = now.strftime("%H_%M_%S")
        return f"{seed}_{clock}.txt"
    else:
        stamp = now.strftime("%Y%m%d_%H%M%S")
        return f"ocr_{stamp}.txt"


def save_text(text: str, out_dir: str, filename: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return out_path


def save_debug_image(img: Image.Image, out_dir: str, filename: str) -> str:
    """Save preprocessed image for debugging."""
    os.makedirs(out_dir, exist_ok=True)
    debug_name = filename.replace('.txt', '_debug.png')
    out_path = os.path.join(out_dir, debug_name)
    img.save(out_path)
    return out_path


# ==================== FILE MODE (for testing) ====================

def process_image_file(image_path: str, output_dir: str = "ocr_output") -> str:
    """Process a single image file - useful for testing."""
    ensure_tesseract_path()

    lang = os.environ.get("OCR_LANG", "eng")
    layout_mode = os.environ.get("OCR_LAYOUT", "grid")
    debug = os.environ.get("OCR_DEBUG", "0") == "1"

    print(f"[OCR] Processing: {image_path}")
    print(f"[OCR] Lang: {lang}, Layout: {layout_mode}, Preprocess: {os.environ.get('OCR_PREPROCESS', 'standard')}")

    img = Image.open(image_path)

    # Save debug image if requested
    if debug:
        processed = preprocess(img)
        debug_path = save_debug_image(processed, output_dir, os.path.basename(image_path))
        print(f"[OCR] Debug image saved: {debug_path}")

    if layout_mode == "grid":
        tsv = ocr_tsv(img, lang=lang)
        text = grid_from_tsv(tsv)
    else:
        text = ocr_text(img, lang=lang)

    # Save output
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    filename = f"{base_name}_ocr.txt"
    out_path = save_text(text, output_dir, filename)

    print(f"[OCR] Output saved: {out_path}")
    print("=" * 50)
    print(text)
    print("=" * 50)

    return text


# ==================== CLIPBOARD WATCH MODE ====================

def main_clipboard():
    """Watch clipboard for images and OCR them."""
    if not HAS_APPKIT:
        print("ERROR: PyObjC required for clipboard watching. Use file mode instead.")
        return

    ensure_tesseract_path()

    lang = os.environ.get("OCR_LANG", "eng")
    interval = float(os.environ.get("OCR_POLL_SEC", "0.5"))
    layout_mode = os.environ.get("OCR_LAYOUT", "grid")
    debug = os.environ.get("OCR_DEBUG", "0") == "1"
    preprocess_method = os.environ.get("OCR_PREPROCESS", "standard")

    pb = NSPasteboard.generalPasteboard()
    last_change = pb.changeCount()
    last_digest: Optional[str] = None
    last_text_seed: Optional[str] = None

    print("[Clipboard OCR] Watching pasteboard... (Ctrl+C to stop)")
    print(f"[Clipboard OCR] Lang: {lang}, Layout: {layout_mode}, Preprocess: {preprocess_method}")
    if debug:
        print("[Clipboard OCR] Debug mode ON - saving preprocessed images")

    while True:
        try:
            current_change = pb.changeCount()
            if current_change != last_change:
                last_change = current_change

                txt = get_pasteboard_text(pb)
                if txt:
                    last_text_seed = sanitize_seed(txt)
                    print(f"[Clipboard OCR] Text seed: '{last_text_seed}'")

                grabbed = grab_pasteboard_image(pb)
                if grabbed:
                    img, source, raw_bytes = grabbed
                    digest = sha256_bytes(raw_bytes)
                    if digest != last_digest:
                        last_digest = digest
                        print(f"[Clipboard OCR] New image from {source}. Running OCR...")
                        try:
                            # Save debug image if enabled
                            if debug:
                                processed = preprocess(img)
                                debug_path = save_debug_image(processed, "ocr_output", f"debug_{digest[:8]}.png")
                                print(f"[Clipboard OCR] Debug: {debug_path}")

                            if layout_mode == "grid":
                                tsv = ocr_tsv(img, lang=lang)
                                text = grid_from_tsv(tsv)
                            else:
                                text = ocr_text(img, lang=lang)

                            filename = build_filename(last_text_seed)
                            out_path = save_text(text, out_dir="ocr_output", filename=filename)
                            print(f"[Clipboard OCR] Saved: {out_path}")

                            if text:
                                print("---------- OCR RESULT ----------")
                                preview = text if len(text) <= 800 else text[:800] + "\n... (truncated)"
                                print(preview)
                                print("------------ END ----------------")
                            else:
                                print("[Clipboard OCR] No text detected")
                        except pytesseract.pytesseract.TesseractNotFoundError:
                            print("ERROR: Tesseract not found. Install via: brew install tesseract")

            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[Clipboard OCR] Stopped.")
            break
        except Exception as e:
            print(f"[Clipboard OCR] Error: {e}")
            time.sleep(max(1.0, interval))


def main():
    import sys

    if len(sys.argv) > 1:
        # File mode - process image file directly
        image_path = sys.argv[1]
        if os.path.isfile(image_path):
            process_image_file(image_path)
        else:
            print(f"ERROR: File not found: {image_path}")
            sys.exit(1)
    else:
        # Clipboard watch mode
        main_clipboard()


if __name__ == "__main__":
    main()
