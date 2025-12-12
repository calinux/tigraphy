#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# IMPROVED OCR LAUNCHER
# =============================================================================
# Fixes:
# - OCR_LANG now uses valid Tesseract values
# - Added OCR_PREPROCESS to select preprocessing method
# - PSM values optimized per mode
# - OCR_DEBUG option to save preprocessed images
# =============================================================================

VENV="/Users/calinux/.venvs/ocr"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Error: $VENV/bin/python not found." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Tesseract path detection
if [[ -x "/opt/homebrew/bin/tesseract" ]]; then
  export TESSERACT_CMD="/opt/homebrew/bin/tesseract"
elif [[ -x "/usr/local/bin/tesseract" ]]; then
  export TESSERACT_CMD="/usr/local/bin/tesseract"
fi

# Default values
export OCR_LANG="${OCR_LANG:-eng}"
export OCR_PSM="${OCR_PSM:-6}"
export OCR_OEM="${OCR_OEM:-3}"
export OCR_DPI="${OCR_DPI:-300}"
export OCR_PRESERVE_SPACES="${OCR_PRESERVE_SPACES:-1}"
export OCR_UPSCALE="${OCR_UPSCALE:-1.5}"
export OCR_THRESH="${OCR_THRESH:-0}"
export OCR_POLL_SEC="${OCR_POLL_SEC:-0.5}"
export OCR_LAYOUT="${OCR_LAYOUT:-grid}"
export OCR_PREPROCESS="${OCR_PREPROCESS:-standard}"
export OCR_DEBUG="${OCR_DEBUG:-0}"

# Interactive menu
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              IMPROVED CLIPBOARD OCR                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Select OCR mode:"
echo ""
echo "  1) Code/Technical - For code, config files, logs, hex dumps"
echo "     (PSM=6, minimal preprocessing, preserves fine details)"
echo ""
echo "  2) Screenshot Clean - For clean UI screenshots"
echo "     (PSM=6, standard preprocessing, high accuracy)"
echo ""
echo "  3) Screenshot Noisy - For low-quality/compressed images"
echo "     (PSM=3, denoising + adaptive threshold)"
echo ""
echo "  4) English Text - For English documents/articles"
echo "     (PSM=3, standard preprocessing)"
echo ""
echo "  5) Romanian Text - For Romanian documents"
echo "     (PSM=3, standard preprocessing)"
echo ""
echo "  6) Custom - Use current environment variables"
echo ""
echo -n "Enter choice (1-6): "
read -r CHOICE

case "$CHOICE" in
  1)
    # CODE/TECHNICAL - optimized for .sln, code, configs, logs
    export OCR_LANG="eng"
    export OCR_PSM="6"              # Uniform block of text
    export OCR_OEM="3"              # LSTM
    export OCR_DPI="300"
    export OCR_PRESERVE_SPACES="1"
    export OCR_UPSCALE="2.0"
    export OCR_THRESH="0"           # No threshold - let Tesseract decide
    export OCR_PREPROCESS="code"    # Special code preprocessing (CLAHE, no blur)
    export OCR_LAYOUT="grid"
    export OCR_DEBUG="1"            # Save debug images to check preprocessing
    echo ""
    echo "[Mode: Code/Technical]"
    echo "  - Preprocessing: code (CLAHE contrast, no blur)"
    echo "  - PSM: 6 (uniform text block)"
    echo "  - Debug images: ON"
    ;;
  2)
    # CLEAN SCREENSHOTS
    export OCR_LANG="eng"
    export OCR_PSM="6"
    export OCR_OEM="3"
    export OCR_DPI="300"
    export OCR_PRESERVE_SPACES="1"
    export OCR_UPSCALE="1.5"
    export OCR_THRESH="0"
    export OCR_PREPROCESS="minimal" # Minimal - just upscale
    export OCR_LAYOUT="grid"
    export OCR_DEBUG="0"
    echo ""
    echo "[Mode: Screenshot Clean]"
    echo "  - Preprocessing: minimal (upscale only)"
    echo "  - PSM: 6 (uniform text block)"
    ;;
  3)
    # NOISY SCREENSHOTS
    export OCR_LANG="eng"
    export OCR_PSM="3"              # Auto-detect layout
    export OCR_OEM="3"
    export OCR_DPI="300"
    export OCR_PRESERVE_SPACES="1"
    export OCR_UPSCALE="2.0"
    export OCR_THRESH="0"
    export OCR_PREPROCESS="noisy"   # Denoise + adaptive threshold
    export OCR_LAYOUT="plain"
    export OCR_DEBUG="1"
    echo ""
    echo "[Mode: Screenshot Noisy]"
    echo "  - Preprocessing: noisy (denoise + adaptive threshold)"
    echo "  - PSM: 3 (auto-detect)"
    echo "  - Debug images: ON"
    ;;
  4)
    # ENGLISH TEXT
    export OCR_LANG="eng"
    export OCR_PSM="3"
    export OCR_OEM="3"
    export OCR_DPI="300"
    export OCR_PRESERVE_SPACES="1"
    export OCR_UPSCALE="1.5"
    export OCR_THRESH="0"
    export OCR_PREPROCESS="standard"
    export OCR_LAYOUT="plain"
    export OCR_DEBUG="0"
    echo ""
    echo "[Mode: English Text]"
    ;;
  5)
    # ROMANIAN TEXT
    export OCR_LANG="ron"
    export OCR_PSM="3"
    export OCR_OEM="3"
    export OCR_DPI="300"
    export OCR_PRESERVE_SPACES="1"
    export OCR_UPSCALE="1.5"
    export OCR_THRESH="0"
    export OCR_PREPROCESS="standard"
    export OCR_LAYOUT="plain"
    export OCR_DEBUG="0"
    echo ""
    echo "[Mode: Romanian Text]"
    echo "  - Requires: tesseract-lang or brew install tesseract-lang"
    ;;
  6)
    echo ""
    echo "[Mode: Custom - using environment variables]"
    ;;
  *)
    echo "Invalid choice. Using defaults."
    ;;
esac

echo ""
echo "Configuration:"
echo "  OCR_LANG=$OCR_LANG"
echo "  OCR_PSM=$OCR_PSM"
echo "  OCR_PREPROCESS=$OCR_PREPROCESS"
echo "  OCR_UPSCALE=$OCR_UPSCALE"
echo "  OCR_THRESH=$OCR_THRESH"
echo "  OCR_LAYOUT=$OCR_LAYOUT"
echo "  OCR_DEBUG=$OCR_DEBUG"
echo ""

# Activate venv
# shellcheck disable=SC1091
source "$VENV/bin/activate"

# Find script
TARGET=""
if [[ -f "clipboard_ocr_improved.py" ]]; then
  TARGET="clipboard_ocr_improved.py"
elif [[ -f "clipboard_ocr_mac.py" ]]; then
  TARGET="clipboard_ocr_mac.py"
elif [[ -f "clipboard_ocr.py" ]]; then
  TARGET="clipboard_ocr.py"
else
  echo "Error: No OCR script found in $SCRIPT_DIR" >&2
  exit 1
fi

echo "[Launcher] Running: $TARGET"
echo ""

# Check for image argument (file mode)
if [[ $# -gt 0 ]]; then
  echo "[Launcher] File mode: $1"
  exec python "$TARGET" "$1"
else
  echo "[Launcher] Clipboard watch mode"
  exec python "$TARGET"
fi
