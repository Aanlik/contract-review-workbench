#!/usr/bin/env bash
set -euo pipefail

ENGINE="${1:-rapid}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$(dirname "$0")/.."

case "$ENGINE" in
  rapid)
    "$PYTHON_BIN" -m pip install -e ".[ocr-rapid]"
    ;;
  rapid-legacy)
    "$PYTHON_BIN" -m pip install -e ".[ocr-rapid-legacy]"
    ;;
  paddle)
    "$PYTHON_BIN" -m pip install -e ".[ocr-paddle]"
    ;;
  all)
    "$PYTHON_BIN" -m pip install -e ".[ocr-all]"
    ;;
  *)
    echo "Usage: $0 [rapid|rapid-legacy|paddle|all]" >&2
    exit 2
    ;;
esac

echo "OCR dependencies installed for: $ENGINE"
echo "Verify with:"
echo "  PYTHONPATH=backend $PYTHON_BIN backend/scripts/ocr_smoke_test.py /path/to/scanned-contract.pdf --engine $ENGINE"
