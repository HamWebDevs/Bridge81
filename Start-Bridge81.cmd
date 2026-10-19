@echo off
setlocal DisableDelayedExpansion
if exist "%LOCALAPPDATA%\Bridge81\Python312\python.exe" goto localpython
py -3.12 -I -c "import tkinter" >nul 2>nul
if not errorlevel 1 goto py312
py -3.11 -I -c "import tkinter" >nul 2>nul
if not errorlevel 1 goto py311
py -3.10 -I -c "import tkinter" >nul 2>nul
if not errorlevel 1 goto py310
python -I -c "import sys,tkinter; sys.exit(sys.version_info < (3,10))" >nul 2>nul
if not errorlevel 1 goto pathpython
echo Bridge81 needs Python 3.10 or later with Tcl/Tk.
echo For Windows 8.1, run Setup-Python.cmd in this folder.
echo Or install Python 3.12.10 from https://www.python.org/downloads/release/python-31210/
echo Choose the traditional installer, with Tcl/Tk enabled.
pause
exit /b 2
:localpython
"%LOCALAPPDATA%\Bridge81\Python312\python.exe" "%~dp0run_bridge81.py" %*
goto finished
:py312
py -3.12 "%~dp0run_bridge81.py" %*
goto finished
:py311
py -3.11 "%~dp0run_bridge81.py" %*
goto finished
:py310
py -3.10 "%~dp0run_bridge81.py" %*
goto finished
:pathpython
python "%~dp0run_bridge81.py" %*
:finished
set "BRIDGE81_EXIT=%errorlevel%"
if not "%BRIDGE81_EXIT%"=="0" pause
exit /b %BRIDGE81_EXIT%
