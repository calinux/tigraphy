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

def mask_colors(img_bgr: np.ndarray) -> np.ndarray:
    """
    Mask colored pixels (icons, UI elements) and keep only grayscale text.
    Returns a grayscale image with colored regions whitened.
    """
    # Convert to HSV to detect saturation
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    # Saturation > 30 means colored pixel
    saturation_threshold = 30
    colored_mask = hsv[:, :, 1] > saturation_threshold

    # Convert to grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Replace colored pixels with white (255)
    gray[colored_mask] = 255

    return gray


def preprocess_minimal(img: Image.Image) -> Image.Image:
    """
    Minimal preprocessing - for clean screenshots with good contrast.
    Only upscales, no thresholding or filters.
    """
    open_cv_image = np.array(img.convert('RGB'))[:, :, ::-1].copy()

    # Optional color masking
    if os.environ.get("OCR_MASK_COLORS", "0") == "1":
        gray = mask_colors(open_cv_image)
    else:
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

    # Optional color masking
    if os.environ.get("OCR_MASK_COLORS", "0") == "1":
        gray = mask_colors(open_cv_image)
    else:
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

    # Optional color masking
    if os.environ.get("OCR_MASK_COLORS", "0") == "1":
        gray = mask_colors(open_cv_image)
    else:
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

    # Optional color masking
    if os.environ.get("OCR_MASK_COLORS", "0") == "1":
        gray = mask_colors(open_cv_image)
    else:
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

# Regex patterns for artifact cleanup
ARTIFACT_PATTERNS = [
    re.compile(r'^[|lI]{3,}$'),           # Repeated | l I (often from icons)
    re.compile(r'^[.\-_=]{4,}$'),         # Repeated . - _ =
    re.compile(r'^[^a-zA-Z0-9]{3,}$'),    # Only special chars (3+)
    re.compile(r'^(.)\1{3,}$'),           # Any char repeated 4+ times
    re.compile(r'^\W{2,}$'),              # Only non-word chars (2+)
]


def is_artifact(text: str) -> bool:
    """Check if text looks like an artifact (icon misread, noise, etc.)."""
    if not text or len(text) < 1:
        return True
    for pattern in ARTIFACT_PATTERNS:
        if pattern.match(text):
            return True
    return False


def grid_from_tsv(tsv_str: str) -> str:
    """Render words to a monospaced grid using TSV word boxes with filtering."""
    # Read filter settings
    conf_min = int(os.environ.get("OCR_CONF_MIN", "50"))
    height_min = int(os.environ.get("OCR_HEIGHT_MIN", "8"))
    height_max = int(os.environ.get("OCR_HEIGHT_MAX", "60"))
    regex_cleanup = os.environ.get("OCR_REGEX_CLEANUP", "1") == "1"

    reader = csv.DictReader(io.StringIO(tsv_str), delimiter='\t')
    words = []
    filtered_count = 0

    for r in reader:
        text = r.get('text', '').strip()
        conf_str = r.get('conf', '-1')
        height_str = r.get('height', '0')

        if not text:
            continue

        try:
            conf = int(float(conf_str))
            height = int(float(height_str))

            # Filter by confidence
            if conf_min > 0 and conf < conf_min:
                filtered_count += 1
                continue

            # Filter by height (bounding box)
            if height_min > 0 and height < height_min:
                filtered_count += 1
                continue
            if height_max > 0 and height > height_max:
                filtered_count += 1
                continue

            # Filter by regex (artifact patterns)
            if regex_cleanup and is_artifact(text):
                filtered_count += 1
                continue

            words.append(r)
        except ValueError:
            pass

    if filtered_count > 0:
        print(f"[Filter] Removed {filtered_count} artifacts (conf<{conf_min}%, height not in {height_min}-{height_max}px, or regex)")

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


def save_text(text: str, out_dir: str, filename: str, append: bool = False) -> str:
    """Save or append text to file."""
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    mode = "a" if append else "w"

    # Check if file exists and has content (for separator)
    add_separator = False
    if append and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        add_separator = True

    with open(out_path, mode, encoding="utf-8", newline="") as f:
        if add_separator:
            f.write("\n\n" + "=" * 50 + "\n\n")  # Separator between entries
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

import threading
import select
import sys

# Available languages for runtime switching
LANGUAGES = {
    '1': ('eng', 'English'),
    '2': ('fra', 'French'),
    '3': ('ron', 'Romanian'),
    '4': ('bod', 'Tibetan'),
    '5': ('eng+bod', 'English + Tibetan'),
}

# Available preprocessing modes
PREPROCESS_MODES = {
    '1': ('minimal', 'Minimal (upscale only)'),
    '2': ('standard', 'Standard'),
    '3': ('code', 'Code/Technical'),
    '4': ('noisy', 'Noisy (denoise + threshold)'),
}


class OCRSettings:
    """Runtime-modifiable OCR settings."""
    def __init__(self):
        self.lang = os.environ.get("OCR_LANG", "eng")
        self.layout = os.environ.get("OCR_LAYOUT", "grid")
        self.preprocess = os.environ.get("OCR_PREPROCESS", "minimal")
        self.preserve_spaces = os.environ.get("OCR_PRESERVE_SPACES", "1") == "1"
        self.concat_mode = os.environ.get("OCR_CONCAT", "1") == "1"
        self.debug = os.environ.get("OCR_DEBUG", "0") == "1"
        # Filtering settings
        self.conf_min = int(os.environ.get("OCR_CONF_MIN", "50"))
        self.height_min = int(os.environ.get("OCR_HEIGHT_MIN", "8"))
        self.height_max = int(os.environ.get("OCR_HEIGHT_MAX", "60"))
        self.mask_colors = os.environ.get("OCR_MASK_COLORS", "0") == "1"
        self.regex_cleanup = os.environ.get("OCR_REGEX_CLEANUP", "1") == "1"
        self.lock = threading.Lock()

    def get_all(self):
        with self.lock:
            return {
                'lang': self.lang,
                'layout': self.layout,
                'preprocess': self.preprocess,
                'preserve_spaces': self.preserve_spaces,
                'concat_mode': self.concat_mode,
                'debug': self.debug,
                'conf_min': self.conf_min,
                'height_min': self.height_min,
                'height_max': self.height_max,
                'mask_colors': self.mask_colors,
                'regex_cleanup': self.regex_cleanup,
            }

    def set_lang(self, lang: str):
        with self.lock:
            self.lang = lang
            os.environ["OCR_LANG"] = lang

    def set_preprocess(self, mode: str):
        with self.lock:
            self.preprocess = mode
            os.environ["OCR_PREPROCESS"] = mode

    def set_conf_min(self, val: int):
        with self.lock:
            self.conf_min = max(0, min(100, val))
            os.environ["OCR_CONF_MIN"] = str(self.conf_min)

    def set_height_range(self, min_h: int, max_h: int):
        with self.lock:
            self.height_min = max(0, min_h)
            self.height_max = max(self.height_min + 1, max_h)
            os.environ["OCR_HEIGHT_MIN"] = str(self.height_min)
            os.environ["OCR_HEIGHT_MAX"] = str(self.height_max)

    def toggle_whitespace(self):
        with self.lock:
            self.preserve_spaces = not self.preserve_spaces
            os.environ["OCR_PRESERVE_SPACES"] = "1" if self.preserve_spaces else "0"
            if self.preserve_spaces:
                self.layout = "grid"
                os.environ["OCR_LAYOUT"] = "grid"
            else:
                self.layout = "plain"
                os.environ["OCR_LAYOUT"] = "plain"
            return self.preserve_spaces

    def toggle_concat(self):
        with self.lock:
            self.concat_mode = not self.concat_mode
            os.environ["OCR_CONCAT"] = "1" if self.concat_mode else "0"
            return self.concat_mode

    def toggle_debug(self):
        with self.lock:
            self.debug = not self.debug
            os.environ["OCR_DEBUG"] = "1" if self.debug else "0"
            return self.debug

    def toggle_mask_colors(self):
        with self.lock:
            self.mask_colors = not self.mask_colors
            os.environ["OCR_MASK_COLORS"] = "1" if self.mask_colors else "0"
            return self.mask_colors

    def toggle_regex_cleanup(self):
        with self.lock:
            self.regex_cleanup = not self.regex_cleanup
            os.environ["OCR_REGEX_CLEANUP"] = "1" if self.regex_cleanup else "0"
            return self.regex_cleanup


class ConcatState:
    """Shared state for concatenation mode."""
    def __init__(self):
        self.current_file: Optional[str] = None
        self.entry_count: int = 0
        self.reset_requested: bool = False
        self.lock = threading.Lock()

    def request_reset(self):
        with self.lock:
            self.reset_requested = True
            print("\n[OCR] >>> New file will be created for next image <<<")

    def check_and_clear_reset(self) -> bool:
        with self.lock:
            if self.reset_requested:
                self.reset_requested = False
                self.current_file = None
                self.entry_count = 0
                return True
            return False

    def set_file(self, filename: str):
        with self.lock:
            self.current_file = filename
            self.entry_count = 1

    def increment(self):
        with self.lock:
            self.entry_count += 1

    def get_info(self) -> Tuple[Optional[str], int]:
        with self.lock:
            return self.current_file, self.entry_count


def print_help():
    """Print available runtime commands."""
    print("""
┌─────────────────────────────────────────────────────────────┐
│                    RUNTIME COMMANDS                         │
├─────────────────────────────────────────────────────────────┤
│  n      - Start NEW file (reset concatenation)              │
│  l      - Change LANGUAGE                                   │
│  m      - Change preprocessing MODE                         │
│  w      - Toggle WHITESPACE preservation                    │
│  c      - Toggle CONCATENATION mode                         │
│  d      - Toggle DEBUG mode                                 │
├───────────────────── FILTERING ─────────────────────────────┤
│  f      - Set confidence FILTER threshold (0-100)           │
│  b      - Set BOUNDING box height filter (min-max)          │
│  k      - Toggle COLOR masking (remove colored pixels)      │
│  r      - Toggle REGEX cleanup (remove artifacts)           │
├─────────────────────────────────────────────────────────────┤
│  s      - Show current SETTINGS                             │
│  h / ?  - Show this HELP                                    │
│  q      - QUIT                                              │
└─────────────────────────────────────────────────────────────┘
""")


def print_settings(settings: OCRSettings, concat_state: ConcatState):
    """Print current settings."""
    s = settings.get_all()
    current_file, entry_count = concat_state.get_info()
    height_range = f"{s['height_min']}-{s['height_max']}px"
    print(f"""
┌─────────────────────────────────────────────────────────────┐
│                   CURRENT SETTINGS                          │
├─────────────────────────────────────────────────────────────┤
│  Language:      {s['lang']:<42} │
│  Preprocess:    {s['preprocess']:<42} │
│  Whitespace:    {'preserved (grid)' if s['preserve_spaces'] else 'collapsed (plain)':<42} │
│  Concatenation: {'ON' if s['concat_mode'] else 'OFF':<42} │
│  Debug:         {'ON' if s['debug'] else 'OFF':<42} │
├───────────────────── FILTERING ─────────────────────────────┤
│  Confidence:    {f">= {s['conf_min']}%":<42} │
│  Height range:  {height_range:<42} │
│  Color mask:    {'ON' if s['mask_colors'] else 'OFF':<42} │
│  Regex cleanup: {'ON' if s['regex_cleanup'] else 'OFF':<42} │
├─────────────────────────────────────────────────────────────┤
│  Current file:  {(current_file or '(none)'):<42} │
│  Entry count:   {entry_count:<42} │
└─────────────────────────────────────────────────────────────┘
""")


def prompt_language_change(settings: OCRSettings):
    """Prompt user to change language."""
    print("\n  Select language:")
    for key, (code, name) in LANGUAGES.items():
        current = " ← current" if code == settings.lang else ""
        print(f"    {key}) {name} ({code}){current}")
    print("    0) Cancel")
    print()


def prompt_preprocess_change(settings: OCRSettings):
    """Prompt user to change preprocessing mode."""
    print("\n  Select preprocessing mode:")
    for key, (mode, name) in PREPROCESS_MODES.items():
        current = " ← current" if mode == settings.preprocess else ""
        print(f"    {key}) {name}{current}")
    print("    0) Cancel")
    print()


def keyboard_listener(settings: OCRSettings, concat_state: ConcatState, stop_event: threading.Event):
    """Listen for keyboard commands."""
    print_help()

    waiting_for_lang = False
    waiting_for_mode = False
    waiting_for_conf = False
    waiting_for_height = False

    while not stop_event.is_set():
        try:
            if select.select([sys.stdin], [], [], 0.5)[0]:
                line = sys.stdin.readline().strip()
                line_lower = line.lower()

                # Handle sub-menus first
                if waiting_for_lang:
                    waiting_for_lang = False
                    if line_lower in LANGUAGES:
                        code, name = LANGUAGES[line_lower]
                        settings.set_lang(code)
                        print(f"[OCR] Language changed to: {name} ({code})")
                    elif line_lower != '0':
                        print("[OCR] Cancelled")
                    continue

                if waiting_for_mode:
                    waiting_for_mode = False
                    if line_lower in PREPROCESS_MODES:
                        mode, name = PREPROCESS_MODES[line_lower]
                        settings.set_preprocess(mode)
                        print(f"[OCR] Preprocessing changed to: {name}")
                    elif line_lower != '0':
                        print("[OCR] Cancelled")
                    continue

                if waiting_for_conf:
                    waiting_for_conf = False
                    try:
                        val = int(line)
                        settings.set_conf_min(val)
                        print(f"[OCR] Confidence threshold set to: >= {settings.conf_min}%")
                    except ValueError:
                        print("[OCR] Invalid number. Cancelled.")
                    continue

                if waiting_for_height:
                    waiting_for_height = False
                    try:
                        parts = line.replace('-', ' ').replace(',', ' ').split()
                        if len(parts) >= 2:
                            min_h, max_h = int(parts[0]), int(parts[1])
                            settings.set_height_range(min_h, max_h)
                            print(f"[OCR] Height filter set to: {settings.height_min}-{settings.height_max}px")
                        else:
                            print("[OCR] Enter two numbers: min max (e.g., '8 40')")
                    except ValueError:
                        print("[OCR] Invalid numbers. Cancelled.")
                    continue

                # Main commands
                if line_lower == 'n':
                    concat_state.request_reset()

                elif line_lower == 'l':
                    prompt_language_change(settings)
                    waiting_for_lang = True

                elif line_lower == 'm':
                    prompt_preprocess_change(settings)
                    waiting_for_mode = True

                elif line_lower == 'w':
                    new_val = settings.toggle_whitespace()
                    status = "ON (grid layout)" if new_val else "OFF (plain layout)"
                    print(f"[OCR] Whitespace preservation: {status}")

                elif line_lower == 'c':
                    new_val = settings.toggle_concat()
                    status = "ON" if new_val else "OFF"
                    print(f"[OCR] Concatenation mode: {status}")

                elif line_lower == 'd':
                    new_val = settings.toggle_debug()
                    status = "ON" if new_val else "OFF"
                    print(f"[OCR] Debug mode: {status}")

                # Filtering commands
                elif line_lower == 'f':
                    s = settings.get_all()
                    print(f"\n  Current confidence threshold: >= {s['conf_min']}%")
                    print("  Enter new value (0-100, 0=disabled):")
                    waiting_for_conf = True

                elif line_lower == 'b':
                    s = settings.get_all()
                    print(f"\n  Current height filter: {s['height_min']}-{s['height_max']}px")
                    print("  Enter new range (min max, e.g., '8 40'):")
                    waiting_for_height = True

                elif line_lower == 'k':
                    new_val = settings.toggle_mask_colors()
                    status = "ON (colored pixels will be masked)" if new_val else "OFF"
                    print(f"[OCR] Color masking: {status}")

                elif line_lower == 'r':
                    new_val = settings.toggle_regex_cleanup()
                    status = "ON" if new_val else "OFF"
                    print(f"[OCR] Regex cleanup: {status}")

                elif line_lower == 's':
                    print_settings(settings, concat_state)

                elif line_lower in ('h', '?'):
                    print_help()

                elif line_lower == 'q':
                    print("[OCR] Quit requested...")
                    stop_event.set()
                    break

        except Exception:
            pass


def main_clipboard():
    """Watch clipboard for images and OCR them."""
    if not HAS_APPKIT:
        print("ERROR: PyObjC required for clipboard watching. Use file mode instead.")
        return

    ensure_tesseract_path()

    # Runtime-modifiable settings
    settings = OCRSettings()
    interval = float(os.environ.get("OCR_POLL_SEC", "0.5"))

    pb = NSPasteboard.generalPasteboard()
    last_change = pb.changeCount()
    last_digest: Optional[str] = None
    last_text_seed: Optional[str] = None

    # Concatenation state
    concat_state = ConcatState()
    stop_event = threading.Event()

    # Always start keyboard listener (for runtime commands)
    kb_thread = threading.Thread(
        target=keyboard_listener,
        args=(settings, concat_state, stop_event),
        daemon=True
    )
    kb_thread.start()

    s = settings.get_all()
    print("[Clipboard OCR] Watching pasteboard... (Ctrl+C or 'q' to stop)")
    print(f"[Clipboard OCR] Lang: {s['lang']}, Layout: {s['layout']}, Preprocess: {s['preprocess']}")
    print("[Clipboard OCR] Type 'h' + Enter for runtime commands")

    while not stop_event.is_set():
        try:
            # Check for reset request
            concat_state.check_and_clear_reset()

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

                        # Get CURRENT settings (may have changed at runtime!)
                        s = settings.get_all()
                        print(f"[Clipboard OCR] New image from {source}. Running OCR (lang={s['lang']}, mode={s['preprocess']})...")

                        try:
                            # Save debug image if enabled
                            if s['debug']:
                                processed = preprocess(img)
                                debug_path = save_debug_image(processed, "ocr_output", f"debug_{digest[:8]}.png")
                                print(f"[Clipboard OCR] Debug: {debug_path}")

                            if s['layout'] == "grid":
                                tsv = ocr_tsv(img, lang=s['lang'])
                                text = grid_from_tsv(tsv)
                            else:
                                text = ocr_text(img, lang=s['lang'])

                            # Handle file saving based on concat mode
                            if s['concat_mode']:
                                current_file, entry_count = concat_state.get_info()
                                if current_file is None:
                                    # Create new file
                                    filename = build_filename(last_text_seed)
                                    concat_state.set_file(filename)
                                    out_path = save_text(text, out_dir="ocr_output", filename=filename, append=False)
                                    print(f"[Clipboard OCR] New file: {out_path}")
                                else:
                                    # Append to existing file
                                    concat_state.increment()
                                    out_path = save_text(text, out_dir="ocr_output", filename=current_file, append=True)
                                    _, count = concat_state.get_info()
                                    print(f"[Clipboard OCR] Appended (#{count}): {out_path}")
                            else:
                                # Non-concat mode: each image = new file
                                filename = build_filename(last_text_seed)
                                out_path = save_text(text, out_dir="ocr_output", filename=filename, append=False)
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
            stop_event.set()
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
