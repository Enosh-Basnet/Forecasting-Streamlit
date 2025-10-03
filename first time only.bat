@echo off
setlocal

REM =======================
REM Hudson's App - Dependency Installer
REM =======================

set "BASE=%~dp0"
set "REQ_FILE=%BASE%app\requirements.txt"
if not exist "%REQ_FILE%" set "REQ_FILE=%BASE%requirements.txt"

if not exist "%REQ_FILE%" (
  echo [!] Could not find requirements.txt in app\ or project root.
  echo Press any key to exit...
  pause >nul
  exit /b 1
)

echo.
echo === Step 1: Show Python version ===
python --version
if %ERRORLEVEL% NEQ 0 (
  echo [!] Python not found on PATH. Install Python first.
  echo Press any key to exit...
  pause >nul
  exit /b 1
)

echo.
echo === Step 2: Upgrade pip, wheel, setuptools ===
python -m pip install --upgrade pip wheel setuptools

echo.
echo === Step 3: Install dependencies from requirements.txt ===
python -m pip install -r "%REQ_FILE%"
if %ERRORLEVEL% NEQ 0 (
  echo [!] Dependency installation failed. Check errors above.
  echo Press any key to exit...
  pause >nul
  exit /b 1
)

echo.
echo ✅ All dependencies installed successfully.
echo Next: run "2 Initialize Database (first time only).bat"
echo Then: run "3 Start App (daily).bat"
echo.
pause
