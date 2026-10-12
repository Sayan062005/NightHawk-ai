@echo off
setlocal enabledelayedexpansion
title NightHawk AI - Operations Control Panel
cd /d "%~dp0"

:: Create logs directory if it does not exist
if not exist "logs" mkdir logs

:: Check if user passed --gui flag to directly open graphical window
if "%~1"=="--gui" goto LAUNCH_GUI_WINDOW
if "%~1"=="gui" goto LAUNCH_GUI_WINDOW

:MAIN_MENU
cls
color 0B
echo.
echo  ===================================================================
echo    _  ___       __   __  __              __      ___   ____
echo   / ^|/ (_)___ _/ /  / / / /___ __    __ / /__   / _ ^| /  _/
echo  /    / / _ `/ _ \/ /_/ / _ `/ ^|/^|/ //  '_/  / __ ^|_/ / 
echo /_/^|_/_/\_, /_//_/\____/\_,_/^|__,__//_/\_\  /_/ ^|_/___/ 
echo        /___/                                             
echo               OPERATIONS CONTROL PANEL & SERVICE MANAGER
echo  ===================================================================
echo.

:: Check ports status
set "B_STATUS=[ OFFLINE ]"
set "F_STATUS=[ OFFLINE ]"

for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    set "B_STATUS=[ ONLINE  ]"
)
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    set "F_STATUS=[ ONLINE  ]"
)

echo   CURRENT SERVICE STATUS:
echo   -------------------------------------------------------------------
echo     * Backend API   (Port 8000) : %B_STATUS%
echo     * Frontend SOC  (Port 3000) : %F_STATUS%
echo   -------------------------------------------------------------------
echo.
echo   [1] START All Services        (Launch Backend & Frontend)
echo   [2] STOP All Services         (Stop running ports 8000 & 3000)
echo   [3] RESTART All Services      (Clean restart of all components)
echo.
echo   [4] VIEW Backend Logs         (Live logs for FastAPI server)
echo   [5] VIEW Frontend Logs        (Live logs for React/Vite UI)
echo.
echo   [6] RUN Autonomous Linux Agent (Test terminal C2 controller)
echo   [7] LAUNCH Desktop Window GUI  (Open clickable Windows GUI app)
echo   [8] OPEN Web Dashboard        (Open http://localhost:3000 in browser)
echo   [9] DOCKER Management         (Docker Compose Up / Down / Logs)
echo.
echo   [0] Exit
echo.
echo  ===================================================================
set /p "CHOICE=  Select an option [0-9]: "

if "%CHOICE%"=="1" goto START_SERVICES
if "%CHOICE%"=="2" goto STOP_SERVICES
if "%CHOICE%"=="3" goto RESTART_SERVICES
if "%CHOICE%"=="4" goto VIEW_BACKEND_LOGS
if "%CHOICE%"=="5" goto VIEW_FRONTEND_LOGS
if "%CHOICE%"=="6" goto RUN_AGENT
if "%CHOICE%"=="7" goto LAUNCH_GUI_WINDOW
if "%CHOICE%"=="8" goto OPEN_BROWSER
if "%CHOICE%"=="9" goto DOCKER_MENU
if "%CHOICE%"=="0" goto EXIT_SCRIPT

echo.
echo   [!] Invalid selection. Please enter a number between 0 and 9.
timeout /t 2 >nul
goto MAIN_MENU


:: ----------------------------------------------------------------------
:: START SERVICES
:: ----------------------------------------------------------------------
:START_SERVICES
cls
echo.
echo   [*] Starting NightHawk AI Services...
echo.

:: 1. Start Backend if not already running
netstat -aon 2>nul | findstr ":8000 " | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo   [+] Backend API is already running on port 8000.
) else (
    echo   [*] Launching Backend API on port 8000...
    powershell -NoProfile -Command "Start-Process -FilePath '%~dp0backend\.venv\Scripts\python.exe' -ArgumentList '-m uvicorn app.main:app --host 127.0.0.1 --port 8000' -WorkingDirectory '%~dp0backend' -RedirectStandardOutput '%~dp0logs\backend.log' -RedirectStandardError '%~dp0logs\backend_err.log' -WindowStyle Hidden"
    echo   [+] Backend started in background.
)

:: 2. Start Frontend if not already running
netstat -aon 2>nul | findstr ":3000 " | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo   [+] Frontend SOC Dashboard is already running on port 3000.
) else (
    echo   [*] Launching Frontend SOC Dashboard on port 3000...
    powershell -NoProfile -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c npm run dev -- --host 127.0.0.1 --port 3000' -WorkingDirectory '%~dp0frontend' -RedirectStandardOutput '%~dp0logs\frontend.log' -RedirectStandardError '%~dp0logs\frontend_err.log' -WindowStyle Hidden"
    echo   [+] Frontend started in background.
)

echo.
echo   [*] Waiting 3 seconds for services to initialize...
timeout /t 3 >nul
goto MAIN_MENU


:: ----------------------------------------------------------------------
:: STOP SERVICES
:: ----------------------------------------------------------------------
:STOP_SERVICES
cls
echo.
echo   [*] Stopping NightHawk AI Services...
echo.

for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   [+] Terminated Backend process on port 8000 (PID: %%a).
)
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   [+] Terminated Frontend process on port 3000 (PID: %%a).
)

echo.
echo   [+] All active services stopped.
timeout /t 2 >nul
goto MAIN_MENU


:: ----------------------------------------------------------------------
:: RESTART SERVICES
:: ----------------------------------------------------------------------
:RESTART_SERVICES
cls
echo.
echo   [*] Executing clean restart sequence...
echo.
call :STOP_SERVICES_SILENT
timeout /t 2 >nul
goto START_SERVICES

:STOP_SERVICES_SILENT
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":3000 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
exit /b


:: ----------------------------------------------------------------------
:: VIEW BACKEND LOGS
:: ----------------------------------------------------------------------
:VIEW_BACKEND_LOGS
cls
echo.
echo   ===================================================================
echo                       NIGHTHAWK AI - BACKEND LOGS
echo   ===================================================================
echo   (Press Ctrl+C to return to main menu)
echo.
if not exist "logs\backend.log" (
    echo   [!] No backend log file found at logs\backend.log.
    pause
    goto MAIN_MENU
)
powershell -NoProfile -Command "Get-Content '%~dp0logs\backend.log' -Tail 30 -Wait"
goto MAIN_MENU


:: ----------------------------------------------------------------------
:: VIEW FRONTEND LOGS
:: ----------------------------------------------------------------------
:VIEW_FRONTEND_LOGS
cls
echo.
echo   ===================================================================
echo                      NIGHTHAWK AI - FRONTEND LOGS
echo   ===================================================================
echo   (Press Ctrl+C to return to main menu)
echo.
if not exist "logs\frontend.log" (
    echo   [!] No frontend log file found at logs\frontend.log.
    pause
    goto MAIN_MENU
)
powershell -NoProfile -Command "Get-Content '%~dp0logs\frontend.log' -Tail 30 -Wait"
goto MAIN_MENU


:: ----------------------------------------------------------------------
:: RUN AUTONOMOUS AGENT
:: ----------------------------------------------------------------------
:RUN_AGENT
cls
echo.
echo   ===================================================================
echo             NIGHTHAWK AI - AUTONOMOUS LINUX RECON AGENT
echo   ===================================================================
echo.
python nighthawk_linux_agent.py
echo.
pause
goto MAIN_MENU


:: ----------------------------------------------------------------------
:: LAUNCH GUI WINDOW
:: ----------------------------------------------------------------------
:LAUNCH_GUI_WINDOW
echo.
echo   [*] Launching NightHawk AI Graphical Desktop Application...
start "" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nighthawk_gui.ps1"
if "%~1"=="--gui" exit /b
if "%~1"=="gui" exit /b
timeout /t 2 >nul
goto MAIN_MENU


:: ----------------------------------------------------------------------
:: OPEN BROWSER
:: ----------------------------------------------------------------------
:OPEN_BROWSER
echo.
echo   [*] Opening NightHawk AI Dashboard in default browser...
start http://localhost:3000
timeout /t 2 >nul
goto MAIN_MENU


:: ----------------------------------------------------------------------
:: DOCKER MANAGEMENT
:: ----------------------------------------------------------------------
:DOCKER_MENU
cls
echo.
echo   ===================================================================
echo                     DOCKER CONTAINER MANAGEMENT
echo   ===================================================================
echo.
echo   [1] docker-compose up -d --build  (Start Docker Stack)
echo   [2] docker-compose down           (Stop Docker Stack)
echo   [3] docker-compose logs -f        (Follow Docker Logs)
echo   [4] Run Automated Docker Tests    (python run_nighthawk_docker.py)
echo   [5] Return to Main Menu
echo.
set /p "DOCKER_CHOICE=  Select option [1-5]: "

if "%DOCKER_CHOICE%"=="1" (
    echo.
    docker compose up -d --build
    pause
    goto DOCKER_MENU
)
if "%DOCKER_CHOICE%"=="2" (
    echo.
    docker compose down
    pause
    goto DOCKER_MENU
)
if "%DOCKER_CHOICE%"=="3" (
    echo.
    docker compose logs -f
    goto DOCKER_MENU
)
if "%DOCKER_CHOICE%"=="4" (
    echo.
    python run_nighthawk_docker.py
    pause
    goto DOCKER_MENU
)
goto MAIN_MENU


:: ----------------------------------------------------------------------
:: EXIT SCRIPT
:: ----------------------------------------------------------------------
:EXIT_SCRIPT
cls
echo.
echo   Thank you for using NightHawk AI. Goodbye!
echo.
timeout /t 1 >nul
exit /b 0
