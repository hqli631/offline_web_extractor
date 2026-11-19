@echo off
setlocal
set "PROJECT_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%PROJECT_PYTHON%" goto run
set "PROJECT_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%PROJECT_PYTHON%" goto run
where python >nul 2>nul
if errorlevel 1 goto missing
set "PROJECT_PYTHON=python"
:run
"%PROJECT_PYTHON%" "%~dp0run.py" %*
exit /b %errorlevel%
:missing
echo Python was not found. Run this project's run.py with a working Python executable. 1>&2
exit /b 1
