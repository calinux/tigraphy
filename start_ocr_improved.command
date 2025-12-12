#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# CLIPBOARD OCR LAUNCHER v3
# =============================================================================
# No questions at startup - just defaults
# All settings modifiable at runtime via keyboard commands
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

# =============================================================================
# DEFAULT VALUES (all modifiable at runtime)
# =============================================================================

# Language & OCR engine
export OCR_LANG="${OCR_LANG:-eng}"
export OCR_PSM="${OCR_PSM:-6}"
export OCR_OEM="${OCR_OEM:-3}"
export OCR_DPI="${OCR_DPI:-300}"

# Preprocessing
export OCR_PREPROCESS="${OCR_PREPROCESS:-minimal}"
export OCR_UPSCALE="${OCR_UPSCALE:-1.5}"
export OCR_THRESH="${OCR_THRESH:-0}"

# Output format
export OCR_PRESERVE_SPACES="${OCR_PRESERVE_SPACES:-1}"
export OCR_LAYOUT="${OCR_LAYOUT:-grid}"
export OCR_CONCAT="${OCR_CONCAT:-1}"

# Filtering (artifact removal)
export OCR_CONF_MIN="${OCR_CONF_MIN:-50}"
export OCR_HEIGHT_MIN="${OCR_HEIGHT_MIN:-8}"
export OCR_HEIGHT_MAX="${OCR_HEIGHT_MAX:-60}"
export OCR_MASK_COLORS="${OCR_MASK_COLORS:-0}"
export OCR_REGEX_CLEANUP="${OCR_REGEX_CLEANUP:-1}"

# Misc
export OCR_DEBUG="${OCR_DEBUG:-0}"
export OCR_POLL_SEC="${OCR_POLL_SEC:-0.5}"
export OCR_WHITELIST="${OCR_WHITELIST:-}"

# =============================================================================
# Activate venv
# =============================================================================
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

# =============================================================================
# Display startup info
# =============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              CLIPBOARD OCR v3                                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ Current Settings (all modifiable at runtime)                │"
echo "├─────────────────────────────────────────────────────────────┤"
echo "│ Language:        $OCR_LANG"
echo "│ Preprocess:      $OCR_PREPROCESS"
echo "│ Whitespace:      $([ "$OCR_PRESERVE_SPACES" = "1" ] && echo "preserved (grid)" || echo "collapsed (plain)")"
echo "│ Concatenation:   $([ "$OCR_CONCAT" = "1" ] && echo "ON" || echo "OFF")"
echo "│ ─────────────────────────────────────────────────────────── │"
echo "│ Confidence min:  ${OCR_CONF_MIN}%"
echo "│ Height filter:   ${OCR_HEIGHT_MIN}-${OCR_HEIGHT_MAX}px"
echo "│ Color masking:   $([ "$OCR_MASK_COLORS" = "1" ] && echo "ON" || echo "OFF")"
echo "│ Regex cleanup:   $([ "$OCR_REGEX_CLEANUP" = "1" ] && echo "ON" || echo "OFF")"
echo "│ Debug:           $([ "$OCR_DEBUG" = "1" ] && echo "ON" || echo "OFF")"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""

# Check for image argument (file mode)
if [[ $# -gt 0 ]]; then
  echo "[Launcher] File mode: $1"
  exec python "$TARGET" "$1"
else
  echo "[Launcher] Starting clipboard watch..."
  exec python "$TARGET"
fi
