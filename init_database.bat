@echo off
setlocal

set BASE=%~dp0
set VENV=%BASE%runtime\venv

echo.
echo === Hudson's App - Initialize Database ===
call "%VENV%\Scripts\activate"

REM Step 1: Run migrations
python -m app.migrations_add_otp

REM Step 2: Create first admin user
python "%BASE%create_admin.py"

deactivate

echo.
echo Database initialized and admin created.
pause
