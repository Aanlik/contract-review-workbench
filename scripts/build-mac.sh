#!/bin/bash
set -e

echo "============================================"
echo "  Contract Review Workbench - macOS Build"
echo "============================================"
echo ""

cd "$(dirname "$0")/.."

PYTHON_BIN=".venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

ARCH="$(uname -m)"
BUILD_ROOT="releases/macos-build-${ARCH}"
PACKAGE_NAME="contract-review-macos-${ARCH}"

if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
  echo "[ERROR] Python 3.11+ not found."
  exit 1
fi

# Install Python deps
echo "[1/5] Installing Python dependencies..."
"$PYTHON_BIN" -m pip install --upgrade pip --quiet
"$PYTHON_BIN" -m pip install -e "backend[ocr-rapid]" pyinstaller --quiet
"$PYTHON_BIN" -c "import rapidocr, onnxruntime; print('RapidOCR imports OK')"

# Build frontend
echo "[2/5] Building frontend..."
cd frontend && npm ci && npm run build && cd ..

# Run PyInstaller
echo "[3/5] Building macOS executable..."
"$PYTHON_BIN" -m PyInstaller backend/contract_review.spec --clean --noconfirm

# Setup data
echo "[4/5] Setting up data directory..."
mkdir -p dist/contract-review/data/storage
printf '%s\n' '# Contract Review Workbench' > dist/contract-review/.env

# Create startup script
echo "[5/5] Creating startup script..."
cat > dist/contract-review/start.sh << 'STARTEOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "=========================================="
echo "  Contract Review Workbench"
echo "  http://127.0.0.1:8000"
echo "=========================================="
echo ""
./contract-review
STARTEOF
chmod +x dist/contract-review/start.sh

echo "[6/6] Creating macOS archive..."
mkdir -p "$BUILD_ROOT"
ditto -c -k --sequesterRsrc --keepParent dist/contract-review "$BUILD_ROOT/${PACKAGE_NAME}.zip"

echo ""
echo "============================================"
echo "  Build complete!"
  echo "  Output: dist/contract-review/"
echo "  Archive: $BUILD_ROOT/${PACKAGE_NAME}.zip"
echo "  Run: ./dist/contract-review/start.sh"
echo "============================================"
