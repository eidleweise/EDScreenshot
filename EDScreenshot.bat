@echo off
setlocal enabledelayedexpansion

rem ==============================================================================
rem  EDScreenshot - Elite Dangerous Screenshot Monitor
rem
rem  This script monitors Elite Dangerous journal files and automatically processes screenshots.
rem  It sets up a Python virtual environment and runs the EDScreenshot.py monitoring service.
rem
rem  USAGE:
rem     EDScreenshot.bat                                   # Run with default configuration
rem     EDScreenshot.bat --name_format "{system}_{timestamp}"  # Custom filename format
rem     EDScreenshot.bat --notification_sound C:\path\to\sound # Custom notification sound
rem
rem  OPTIONAL ARGUMENTS:
rem
rem     --name_format <FORMAT>
rem         Filename format template for processed screenshots.
rem         Available placeholders:
rem           {system}    - Star system name
rem           {body}      - Body name
rem           {timestamp} - Combined date+time as YYYYMMDD_HHMMSS
rem           {date}      - Date as YYYY-MM-DD
rem           {time}      - Time as HH-MM-SS
rem           {datetime}  - Date and time as YYYY-MM-DD_HH-MM-SS
rem         Default: "{system}_{body}_{timestamp}"
rem         Example: --name_format "{system}_{body}_{timestamp}"
rem
rem     --notification_sound <PATH>
rem         Path to a sound file to play after processing a screenshot.
rem         Supported formats: .ogg, .wav, .mp3
rem         If not provided, no sound will be played after screenshots are processed.
rem         Example: --notification_sound "C:\path\to\sound.ogg"
rem
rem  ENVIRONMENT CONFIGURATION:
rem
rem     The following variables can be edited in this script for custom configuration:
rem
rem       JOURNAL_FOLDER        - Path to Elite Dangerous journal files
rem       SCREENSHOT_FOLDER     - Path to Elite Dangerous screenshots
rem       EXPORT_FORMAT         - Output format: PNG, JPG, or JXL (default: PNG)
rem       CREATE_SYSTEM_FOLDER  - Organize screenshots by system folder (default: TRUE)
rem ==============================================================================

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "VENV_PATH=%PROJECT_DIR%\.venv"
set "LOG_FILE=%PROJECT_DIR%\ed_screenshot.log"

rem --- Default Windows Paths ---
set "JOURNAL_FOLDER=%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous"
set "SCREENSHOT_FOLDER=%USERPROFILE%\Pictures\Frontier Developments\Elite Dangerous"
set "EXPORT_FORMAT=PNG"
set "CREATE_SYSTEM_FOLDER=TRUE"
set "NAME_FORMAT={system}_{body}_{timestamp}"
set "NOTIFICATION_SOUND=%PROJECT_DIR%\resources\Instant_Click.ogg"

rem --- Parse Arguments ---
:parse_args
if "%~1"=="" goto end_parse
if "%~1"=="--name_format" (
    set "NAME_FORMAT=%~2"
    shift & shift
    goto parse_args
)
if "%~1"=="--notification_sound" (
    set "NOTIFICATION_SOUND=%~2"
    shift & shift
    goto parse_args
)
shift
goto parse_args
:end_parse

rem --- Initialization ---
call :log INFO "Starting EDScreenshot..."

rem --- Virtual Environment ---
if exist "%VENV_PATH%" (
    "%VENV_PATH%\Scripts\python.exe" --version >nul 2>&1
    if errorlevel 1 (
        call :log WARN "Virtual environment is corrupted. Recreating..."
        rmdir /s /q "%VENV_PATH%"
    )
)

if not exist "%VENV_PATH%" (
    call :log INFO "Creating virtual environment..."
    python -m venv "%VENV_PATH%" >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        call :log ERROR "Failed to create venv"
        exit /b 1
    )
)

rem --- Dependencies ---
call :log INFO "Checking dependencies..."
"%VENV_PATH%\Scripts\pip.exe" install -q -r "%PROJECT_DIR%\requirements.txt" >> "%LOG_FILE%" 2>&1

if errorlevel 1 (
    call :log ERROR "Pip install failed. Check ed_screenshot.log"
    exit /b 1
)

call :log SUCCESS "Environment ready."

rem --- Run ---
call :log INFO "Monitoring: %JOURNAL_FOLDER%"

"%VENV_PATH%\Scripts\python.exe" -u "%PROJECT_DIR%\EDScreenshot.py" ^
    "%JOURNAL_FOLDER%" ^
    "%SCREENSHOT_FOLDER%" ^
    "%EXPORT_FORMAT%" ^
    "%CREATE_SYSTEM_FOLDER%" ^
    --name_format "%NAME_FORMAT%" ^
    --notification_sound "%NOTIFICATION_SOUND%"

set "PYTHON_EXIT_CODE=%errorlevel%"

if %PYTHON_EXIT_CODE% equ 0 (
    call :log SUCCESS "Task completed successfully."
) else (
    call :log ERROR "Python script exited with an error code: %PYTHON_EXIT_CODE%"
)

endlocal
exit /b %PYTHON_EXIT_CODE%

rem --- Logging Function ---
:log
set "LEVEL=%~1"
set "MSG=%~2"
set "TIME_STAMP=%time:~0,8%"

if "%LEVEL%"=="INFO"    echo [%TIME_STAMP%] [INFO] %MSG%
if "%LEVEL%"=="SUCCESS" echo [%TIME_STAMP%] [SUCCESS] %MSG%
if "%LEVEL%"=="WARN"    echo [%TIME_STAMP%] [WARN] %MSG%
if "%LEVEL%"=="ERROR"   echo [%TIME_STAMP%] [ERROR] %MSG%

echo [%TIME_STAMP%] %LEVEL%: %MSG% >> "%LOG_FILE%"
goto :eof