@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -B -m southpaw_tools.server %*
) else (
  python -B -m southpaw_tools.server %*
)
exit /b %errorlevel%
