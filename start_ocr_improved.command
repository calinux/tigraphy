#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# IMPROVED OCR LAUNCHER v2
# =============================================================================
# Two-step selection:
# 1. Content type (preprocessing method)
# 2. Language
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
export OCR_WHITELIST="${OCR_WHITELIST:-}"

# =============================================================================
# STEP 1: Content Type Selection
# =============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              IMPROVED CLIPBOARD OCR v2                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ STEP 1: Select content type                                 │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "  1) Technical/Code    - Code, configs, logs, .sln files"
echo "                         (preserves fine details, grid layout)"
echo ""
echo "  2) Token/Key/Hex     - Tokens, API keys, hex dumps, no language"
echo "                         (character-only, no dictionary)"
echo ""
echo "  3) Document Clean    - Clean scanned documents, screenshots"
echo "                         (minimal preprocessing)"
echo ""
echo "  4) Document Noisy    - Low-quality scans, photos of text"
echo "                         (denoising + adaptive threshold)"
echo ""
echo "  5) Custom            - Use environment variables"
echo ""
echo -n "Enter choice (1-5): "
read -r CONTENT_CHOICE

case "$CONTENT_CHOICE" in
  1)
    # CODE/TECHNICAL
    export OCR_PSM="6"
    export OCR_OEM="3"
    export OCR_DPI="300"
    export OCR_PRESERVE_SPACES="1"
    export OCR_UPSCALE="2.0"
    export OCR_THRESH="0"
    export OCR_PREPROCESS="code"
    export OCR_LAYOUT="grid"
    export OCR_DEBUG="1"
    export OCR_WHITELIST=""
    CONTENT_DESC="Technical/Code"
    ;;
  2)
    # TOKEN/KEY/HEX - No language model, just characters
    export OCR_PSM="6"
    export OCR_OEM="3"
    export OCR_DPI="300"
    export OCR_PRESERVE_SPACES="1"
    export OCR_UPSCALE="2.0"
    export OCR_THRESH="0"
    export OCR_PREPROCESS="code"
    export OCR_LAYOUT="grid"
    export OCR_DEBUG="1"
    # Whitelist: alphanumeric + common token chars
    export OCR_WHITELIST="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_=+/:.@#$%&*()[]{}|\\<>,;\"'"
    CONTENT_DESC="Token/Key/Hex"
    ;;
  3)
    # DOCUMENT CLEAN
    export OCR_PSM="3"
    export OCR_OEM="3"
    export OCR_DPI="300"
    export OCR_PRESERVE_SPACES="1"
    export OCR_UPSCALE="1.5"
    export OCR_THRESH="0"
    export OCR_PREPROCESS="minimal"
    export OCR_LAYOUT="plain"
    export OCR_DEBUG="0"
    export OCR_WHITELIST=""
    CONTENT_DESC="Document Clean"
    ;;
  4)
    # DOCUMENT NOISY
    export OCR_PSM="3"
    export OCR_OEM="3"
    export OCR_DPI="300"
    export OCR_PRESERVE_SPACES="1"
    export OCR_UPSCALE="2.0"
    export OCR_THRESH="0"
    export OCR_PREPROCESS="noisy"
    export OCR_LAYOUT="plain"
    export OCR_DEBUG="1"
    export OCR_WHITELIST=""
    CONTENT_DESC="Document Noisy"
    ;;
  5)
    CONTENT_DESC="Custom"
    ;;
  *)
    echo "Invalid choice. Using defaults."
    CONTENT_DESC="Default"
    ;;
esac

echo ""
echo "[Content: $CONTENT_DESC]"

# =============================================================================
# STEP 2: Language Selection
# =============================================================================
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ STEP 2: Select language                                     │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "  1) English           (eng)"
echo "  2) French            (fra)"
echo "  3) Romanian          (ron)"
echo "  4) Tibetan           (bod)"
echo "  5) English + Tibetan (eng+bod)"
echo "  6) None/Raw          (no language model - for tokens/hex)"
echo "  7) Custom            (enter manually)"
echo ""
echo -n "Enter choice (1-7): "
read -r LANG_CHOICE

case "$LANG_CHOICE" in
  1)
    export OCR_LANG="eng"
    LANG_DESC="English"
    ;;
  2)
    export OCR_LANG="fra"
    LANG_DESC="French"
    ;;
  3)
    export OCR_LANG="ron"
    LANG_DESC="Romanian"
    ;;
  4)
    export OCR_LANG="bod"
    LANG_DESC="Tibetan"
    ;;
  5)
    export OCR_LANG="eng+bod"
    LANG_DESC="English + Tibetan"
    ;;
  6)
    # No language model - use OSD (orientation/script detection) only
    # or eng with whitelist
    export OCR_LANG="eng"
    export OCR_WHITELIST="${OCR_WHITELIST:-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_=+/:.@#}"
    LANG_DESC="None/Raw (whitelist only)"
    ;;
  7)
    echo -n "Enter Tesseract language code (e.g., deu, spa, eng+fra): "
    read -r CUSTOM_LANG
    export OCR_LANG="${CUSTOM_LANG:-eng}"
    LANG_DESC="Custom: $OCR_LANG"
    ;;
  *)
    echo "Invalid choice. Using English."
    export OCR_LANG="eng"
    LANG_DESC="English (default)"
    ;;
esac

echo ""
echo "[Language: $LANG_DESC]"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ Configuration Summary                                       │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "  Content type:    $CONTENT_DESC"
echo "  Language:        $LANG_DESC"
echo "  OCR_LANG:        $OCR_LANG"
echo "  OCR_PSM:         $OCR_PSM"
echo "  OCR_PREPROCESS:  $OCR_PREPROCESS"
echo "  OCR_UPSCALE:     $OCR_UPSCALE"
echo "  OCR_LAYOUT:      $OCR_LAYOUT"
echo "  OCR_DEBUG:       $OCR_DEBUG"
if [[ -n "$OCR_WHITELIST" ]]; then
  echo "  OCR_WHITELIST:   (set - ${#OCR_WHITELIST} chars)"
fi
echo ""

# =============================================================================
# Check required language packs
# =============================================================================
check_lang_installed() {
  local lang="$1"
  # Handle combined languages like eng+bod
  for l in ${lang//+/ }; do
    if ! "$TESSERACT_CMD" --list-langs 2>/dev/null | grep -q "^${l}$"; then
      echo "⚠️  Warning: Language '$l' may not be installed."
      echo "   Install with: brew install tesseract-lang"
      echo ""
    fi
  done
}

if [[ -n "${TESSERACT_CMD:-}" ]]; then
  check_lang_installed "$OCR_LANG"
fi

# =============================================================================
# Activate venv and run
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

echo "[Launcher] Running: $TARGET"
echo ""

# Check for image argument (file mode)
if [[ $# -gt 0 ]]; then
  echo "[Launcher] File mode: $1"
  exec python "$TARGET" "$1"
else
  echo "[Launcher] Clipboard watch mode - press Ctrl+C to stop"
  echo ""
  exec python "$TARGET"
fi
