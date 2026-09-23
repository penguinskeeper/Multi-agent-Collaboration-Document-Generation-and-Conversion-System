@echo off
setlocal
REM ============================================================
REM  Deep Search Pro - API server launcher
REM
REM  Open in browser after start:
REM    http://localhost:8000/       demo page (chat + live timeline)
REM    http://localhost:8000/docs   interactive API docs
REM
REM  KEEP THIS WINDOW OPEN while using the project.
REM  Press Ctrl+C to stop the server. Closing the window is NOT a
REM  reliable stop: it may only kill cmd.exe and leave python.exe
REM  holding port 8000 (the next start then fails with
REM  "address already in use"). To stop everything at once, run
REM  stop_all.bat instead.
REM
REM  Prerequisite: MySQL must be running on port 3306,
REM  otherwise the database sub-agent will fail.
REM
REM  ------------------------------------------------------------
REM  Interpreter resolution
REM  ------------------------------------------------------------
REM  The dependencies (uvicorn, langchain, deepagents ...) live in
REM  ONE specific environment, but a machine often has several
REM  other Pythons on PATH. Picking the wrong one is the single
REM  most common startup failure ("No module named uvicorn").
REM
REM  So instead of trusting the first "python" found on PATH, every
REM  candidate below is actually executed and checked for uvicorn.
REM  The first one that passes wins, in this order:
REM
REM    1. %DSP_PYTHON%               explicit override, e.g.
REM                                  set DSP_PYTHON=C:\path\to\python.exe
REM    2. .venv\Scripts\python.exe   project venv (recommended)
REM    3. .dsp-python.txt            one-line local override file
REM                                  (gitignored). Use it when your
REM                                  dependencies live outside the
REM                                  project and you would rather not
REM                                  set a system-wide variable.
REM    4. python / py on PATH        accepted only if it has uvicorn
REM
REM  If none of them works the script stops with a clear message,
REM  instead of limping along and failing on the first request.
REM ============================================================

cd /d "%~dp0"

set "PY="

REM 1) explicit override
if defined DSP_PYTHON call :try_py "%DSP_PYTHON%"

REM 2) project-local virtualenv
if not defined PY if exist "%~dp0.venv\Scripts\python.exe" call :try_py "%~dp0.venv\Scripts\python.exe"

REM 3) machine-local override file (read the first line)
if not defined PY call :try_local_file

REM 4) last resort: whatever is on PATH - only if it really has uvicorn
if not defined PY call :try_py "python"
if not defined PY call :try_py "py"

if not defined PY goto :no_interpreter
goto :launch


REM ------------------------------------------------------------
REM  Subroutines
REM ------------------------------------------------------------

:try_local_file
if not exist "%~dp0.dsp-python.txt" goto :eof
set "LOCALPY="
set /p LOCALPY=<"%~dp0.dsp-python.txt"
call :try_py "%LOCALPY%"
goto :eof

:try_py
set "CAND=%~1"
if "%CAND%"=="" goto :eof
"%CAND%" -c "import uvicorn" >nul 2>&1
if errorlevel 1 goto :eof
set "PY=%CAND%"
goto :eof


REM ------------------------------------------------------------
REM  Failure path
REM ------------------------------------------------------------

:no_interpreter
echo.
echo [ERROR] No Python interpreter with 'uvicorn' was found.
echo.
echo   Tried, in order:
echo     1. %%DSP_PYTHON%%  (not set)
echo     2. .venv\Scripts\python.exe  (not found)
echo     3. .dsp-python.txt  (not found or not usable)
echo     4. python / py on PATH  (no uvicorn)
echo.
echo   Fix it with either approach:
echo.
echo     A) Create the project venv (recommended, portable)
echo          python -m venv .venv
echo          .venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
echo     B) Point this launcher at the interpreter you already use,
echo        and record it in a gitignored one-line file:
echo          echo C:\path\to\python.exe ^> .dsp-python.txt
echo        (or set the DSP_PYTHON environment variable instead)
echo.
echo   On a machine with several Pythons, verify a candidate with:
echo          "C:\path\to\python.exe" -c "import uvicorn"
echo.
pause
endlocal
exit /b 1


REM ------------------------------------------------------------
REM  Launch
REM ------------------------------------------------------------

:launch
echo Starting Deep Search Pro API server on port 8000 ...
echo   interpreter: %PY%
echo.

"%PY%" -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --log-level info

echo.
echo [Server stopped]
pause
endlocal
exit /b 0
