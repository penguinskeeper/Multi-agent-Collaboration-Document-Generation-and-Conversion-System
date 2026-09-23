@echo off
setlocal
REM ============================================================
REM  Deep Search Pro - one click launcher
REM
REM  What it does:
REM    1) starts MySQL 8.4 in a new window
REM    2) starts the API server in a new window
REM    3) opens the demo page in your browser
REM
REM  TWO WINDOWS WILL POP UP - keep them open while testing.
REM  To stop everything, run stop_all.bat (do NOT just close the
REM  windows: that can leave mysqld running and skip a clean
REM  InnoDB shutdown).
REM
REM  Set MYSQL_HOME first if your MySQL is not at D:\MySQL:
REM      set MYSQL_HOME=C:\path\to\mysql
REM
REM  This script does not choose a Python itself - the API window does,
REM  inside start_api.bat, by testing each candidate for the uvicorn
REM  module. If that window reports "No module named uvicorn", either
REM  set DSP_PYTHON or drop a one-line .dsp-python.txt in this folder.
REM ============================================================

setlocal

REM  MySQL install location - override with MYSQL_HOME
if not defined MYSQL_HOME set "MYSQL_HOME=D:\MySQL"
set "MYSQL_START=%MYSQL_HOME%\start_mysql.bat"

echo ==================================================
echo   Deep Search Pro - starting everything
echo ==================================================
echo.

if exist "%MYSQL_START%" (
  echo [1/3] Starting MySQL 8.4 ^(port 3306^) ...
  start "MySQL 8.4 - Deep Search Pro" cmd /k call "%MYSQL_START%"
  timeout /t 12 /nobreak >nul
) else (
  echo [1/3] Skipped - MySQL launcher not found:
  echo         %MYSQL_START%
  echo         Set MYSQL_HOME to your MySQL folder, or start MySQL
  echo         yourself. The app still runs, but the database
  echo         sub-agent will be disabled.
  echo.
)

echo [2/3] Starting API server (port 8000) ...
start "Deep Search API - Deep Search Pro" cmd /k call "%~dp0start_api.bat"
timeout /t 10 /nobreak >nul

echo [3/3] Opening browser ...
start "" http://localhost:8000/

echo.
echo --------------------------------------------------
echo  Done. Two new windows were opened:
echo    1) MySQL 8.4        - database, keep open
echo    2) Deep Search API  - web server, keep open
echo.
echo  Demo page : http://localhost:8000/
echo  API docs  : http://localhost:8000/docs
echo.
echo  If the browser shows an error, wait 10 more seconds
echo  and press F5 (refresh).
echo.
echo  To stop: run stop_all.bat
echo --------------------------------------------------
echo.

pause
endlocal
