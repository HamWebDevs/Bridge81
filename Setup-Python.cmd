@echo off
setlocal DisableDelayedExpansion
echo This installs a private, per-user Python 3.12.10 runtime for Bridge81.
echo It downloads only from Python.org and checks the file before running it.
echo No administrator account or PATH changes are requested by this script.
echo.
pause
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Setup-Python.ps1"
set "BRIDGE81_SETUP_EXIT=%errorlevel%"
echo.
if not "%BRIDGE81_SETUP_EXIT%"=="0" echo Setup did not complete. See the message above or docs\windows81.md.
if "%BRIDGE81_SETUP_EXIT%"=="0" echo Ready. Double-click Start-Bridge81.cmd to open the app.
pause
exit /b %BRIDGE81_SETUP_EXIT%
