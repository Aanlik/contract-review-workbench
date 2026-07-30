@echo off
setlocal

echo ============================================
echo   Contract Review Workbench - Windows Build
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ and add to PATH.
    pause
    exit /b 1
)

:: Install dependencies
echo [1/5] Installing Python dependencies...
pip install fastapi uvicorn sqlalchemy pydantic-settings python-multipart httpx pymupdf pillow python-docx cryptography alembic
pip install pyinstaller

:: Build frontend
echo [2/5] Building frontend...
cd frontend
call npm install
call npm run build
cd ..

:: Run PyInstaller
echo [3/5] Building Windows executable...
pyinstaller backend\contract_review.spec --clean --noconfirm

:: Copy data template
echo [4/5] Setting up data directory...
if not exist "dist\contract-review\data" mkdir "dist\contract-review\data"
if not exist "dist\contract-review\data\storage" mkdir "dist\contract-review\data\storage"

:: Create startup script
echo [5/5] Creating startup script...
(
echo @echo off
echo title Contract Review Workbench
echo echo ==========================================
echo echo   Contract Review Workbench
echo echo   http://127.0.0.1:8000
echo echo ==========================================
echo echo.
echo contract-review.exe
echo pause
) > "dist\contract-review\start.bat"

echo.
echo ============================================
echo   Build complete!
echo   Output: dist\contract-review\
echo   Run: dist\contract-review\start.bat
echo ============================================
pause
