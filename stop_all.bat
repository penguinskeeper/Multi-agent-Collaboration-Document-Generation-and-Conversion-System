@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  Deep Search Pro - one click stopper
REM
REM  Stops BOTH services that start_all.bat launched:
REM    1) API server  (python / uvicorn  on port 8000)
REM    2) MySQL 8.4   (mysqld           on port 3306, graceful)
REM
REM  WHY THIS EXISTS:
REM    start_mysql.bat runs "mysqld.exe --console" as a foreground
REM    process, and ends with "pause". Closing that console window
REM    is NOT a reliable stop: Windows gives the process only a few
REM    seconds to handle the close event, MySQL may still be doing a
REM    fast shutdown, and the port can stay bound for a while. It can
REM    also leave InnoDB needing crash recovery on next start.
REM
REM    MySQL is therefore stopped with "mysqladmin shutdown" first
REM    (clean flush), and only force-killed if that times out.
REM
REM  Usage: double click this file. Read the report at the bottom.
REM ============================================================

REM  MySQL install location. Override before running if yours differs:
REM      set MYSQL_HOME=C:\path\to\mysql
if not defined MYSQL_HOME set "MYSQL_HOME=D:\MySQL"
set "MYSQL_BIN=%MYSQL_HOME%\mysql-8.4.6-winx64\bin"

REM  Credentials are NEVER hard-coded in this script. The root password is read
REM  from the environment so it cannot leak into the repository. Set it once
REM  with:  setx MYSQL_ROOT_PWD yourpassword
REM  (then open a new console so the variable becomes visible).

echo ==================================================
echo   Deep Search Pro - stopping everything
echo ==================================================
echo.

REM ---------- 1) API server on port 8000 ----------
call :portpid 8000 API_PID
if defined API_PID (
  echo [1/3] Stopping API server ^(PID !API_PID! on port 8000^) ...
  taskkill /F /T /PID !API_PID! >nul 2>&1
) else (
  echo [1/3] Nothing listening on 8000 - sweeping leftovers ...
)
REM  Why the sweep: "uvicorn --reload" and "python api\server.py" run a
REM  RELOADER PARENT that respawns the worker the moment the worker dies.
REM  Killing only the port owner therefore leaves the port coming back.
REM  Only processes named python*.exe are matched, so this can never touch
REM  the console windows or any unrelated program.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'uvicorn|api[\\/]server\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
echo        done.

REM ---------- 2) MySQL on port 3306 ----------
call :portpid 3306 MYSQL_PID
if defined MYSQL_PID (
  if not defined MYSQL_ROOT_PWD set /p "MYSQL_ROOT_PWD=  MySQL root password [Enter = skip graceful stop]: "
  if not defined MYSQL_ROOT_PWD (
    echo [2/3] MYSQL_ROOT_PWD not set - forcing termination ^(InnoDB recovery on next start^) ...
    taskkill /F /IM mysqld.exe >nul 2>&1
    call :waitport 3306 5
    echo        done.
  ) else (
    echo [2/3] Shutting down MySQL gracefully ^(PID !MYSQL_PID!^) ...
    set "MYSQL_PWD=!MYSQL_ROOT_PWD!"
    "%MYSQL_BIN%\mysqladmin.exe" -u root -h 127.0.0.1 shutdown 1>nul 2>&1
    set "MYSQL_PWD="
    call :waitport 3306 5
    call :portpid 3306 STILL_PID
    if defined STILL_PID (
      echo        Graceful shutdown did not finish in time.
      echo        Forcing termination ^(next start will do InnoDB recovery^) ...
      taskkill /F /IM mysqld.exe >nul 2>&1
      call :waitport 3306 5
      echo        done.
    ) else (
      echo        MySQL stopped cleanly.
    )
  )
) else (
  echo [2/3] MySQL is not running - skipped.
)

REM ---------- 3) leftover console windows ----------
echo [3/3] Closing leftover service windows ...
taskkill /F /FI "WINDOWTITLE eq MySQL 8.4 - Deep Search Pro*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Deep Search API - Deep Search Pro*" >nul 2>&1

echo.
echo --------------------------------------------------
call :report 3306 "MySQL      "
call :report 8000 "API server "
echo --------------------------------------------------
echo  FREE on both lines = everything is fully stopped.
echo  STILL LISTENING     = stop it manually, see below.
echo.
echo  Manual fallback if a port is still held:
echo    netstat -ano ^| findstr ":3306 :8000"
echo    taskkill /F /PID ^<the PID in the last column^>
echo.
echo  If MySQL was registered as a Windows service instead:
echo    net stop MySQL84        ^(needs an Administrator window^)
echo.
echo  To avoid being asked for the password every time:
echo    setx MYSQL_ROOT_PWD yourpassword
echo  (opens a new console to take effect; keep it out of version control)
echo.
pause
endlocal
exit /b 0

REM ================= helpers =================

:portpid  %1=port  %2=varname to receive PID
set "%~2="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%~1 " ^| findstr "LISTENING"') do set "%~2=%%p"
exit /b 0

:waitport  %1=port  %2=max attempts (2s each)
set /a _wp=0
:waitport_loop
netstat -ano | findstr ":%~1 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 exit /b 0
set /a _wp+=1
if !_wp! GEQ %~2 exit /b 0
timeout /t 2 /nobreak >nul
goto waitport_loop

:report  %1=port  %2=label
netstat -ano | findstr ":%~1 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
  echo  %~2 port %~1 : FREE
) else (
  echo  %~2 port %~1 : STILL LISTENING
)
exit /b 0
