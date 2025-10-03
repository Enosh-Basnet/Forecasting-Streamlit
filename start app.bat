@echo off
setlocal

REM ============================
REM Hudson's App - Start (No venv)
REM ============================

REM --- Paths ---
set "BASE=%~dp0"
set "ENVFILE=%BASE%app\scripts\.env.local"

REM --- Require Python on PATH ---
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo [!] Python not found on PATH.
  echo     Install Python and run "1 Install (first time only).bat" to install deps.
  pause
  exit /b 1
)

REM --- Ports (defaults) ---
set "STREAMLIT_PORT=8501"
set "API_PORT=8000"

if exist "%ENVFILE%" (
  for /f "tokens=1,2 delims==" %%A in ('type "%ENVFILE%" ^| findstr /b /r "STREAMLIT_PORT= API_PORT="') do (
    if /i "%%A"=="STREAMLIT_PORT" set "STREAMLIT_PORT=%%B"
    if /i "%%A"=="API_PORT" set "API_PORT=%%B"
  )
)

echo.
echo === Starting Hudson's App (no venv) ===
echo Using STREAMLIT_PORT=%STREAMLIT_PORT%
echo Using API_PORT=%API_PORT%

REM --- Start FastAPI (optional) ---
if exist "%BASE%app\api\main.py" (
  start "Hudsons API" cmd /k ^
    "python -m uvicorn app.api.main:app --host 127.0.0.1 --port %API_PORT% --reload"
) else (
  echo (No FastAPI backend detected - skipping)
)

REM --- Start Streamlit UI (use -m so we don't rely on Scripts\ on PATH) ---
if exist "%BASE%app\ui_app.py" (
  start "Hudsons UI" cmd /k ^
    "python -m streamlit run app\ui_app.py --server.port %STREAMLIT_PORT% --server.headless true"
) else (
  echo [!] app\ui_app.py not found. Make sure your Streamlit entry file exists.
  pause
  exit /b 1
)

REM --- Open Browser ---
start "" http://localhost:%STREAMLIT_PORT%

echo.
echo App launched. Close the two console windows (API/UI) to stop.
