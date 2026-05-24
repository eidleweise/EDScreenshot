#!/bin/bash

# --- Configuration ---
PROJECT_DIR="/home/ben/PycharmProjects/EDScreenshot"
VENV_PATH="$PROJECT_DIR/.venv"
LOG_FILE="$PROJECT_DIR/ed_screenshot.log"

# --- Colors for Console Output ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Logging Function ---
log() {
    local LEVEL=$1
    local MSG=$2
    local TIMESTAMP=$(date '+%H:%M:%S')

    # Print to Console with colors
    case $LEVEL in
        "INFO")    echo -e "${BLUE}[$TIMESTAMP]${NC} $MSG" ;;
        "SUCCESS") echo -e "${GREEN}[$TIMESTAMP] $MSG${NC}" ;;
        "WARN")    echo -e "${YELLOW}[$TIMESTAMP] $MSG${NC}" ;;
        "ERROR")   echo -e "${RED}[$TIMESTAMP] ERROR: $MSG${NC}" ;;
    esac

    # Also append to log file (plain text)
    echo "[$TIMESTAMP] $LEVEL: $MSG" >> "$LOG_FILE"
}

# --- Initialization ---
clear
log "INFO" "Starting EDScreenshot Task..."

# --- 1. Virtual Environment Check & Validation ---
if [ -d "$VENV_PATH" ]; then
    log "INFO" "Validating existing virtual environment..."
    # Try to run a simple command; if it fails (bad interpreter), we recreate it
    "$VENV_PATH/bin/python" --version > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        log "WARN" "Virtual environment is corrupted (Bad Interpreter). Recreating..."
        rm -rf "$VENV_PATH"
    fi
fi

if [ ! -d "$VENV_PATH" ]; then
    log "INFO" "Creating virtual environment at $VENV_PATH..."
    python3 -m venv "$VENV_PATH" >> "$LOG_FILE" 2>&1
    if [ $? -ne 0 ]; then log "ERROR" "Failed to create venv"; exit 1; fi
fi

# 2. Dependency Check (Silent unless error)
log "INFO" "Verifying Python dependencies..."
"$VENV_PATH/bin/pip" install -q -r "$PROJECT_DIR/requirements.txt" >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "SUCCESS" "Environment is ready."
else
    log "ERROR" "Pip install failed. Check $LOG_FILE"
    exit 1
fi

# 3. Path Variables
JOURNAL_FOLDER="/run/media/system/Games/WinePrefixes/elite-dangerous/drive_c/users/steamuser/Saved Games/Frontier Developments/Elite Dangerous/"
SCREENSHOT_FOLDER="/run/media/system/Games/WinePrefixes/elite-dangerous/drive_c/users/steamuser/Pictures/Frontier Developments/Elite Dangerous/"
EXPORT_FORMAT="PNG"
CREATE_SYSTEM_FOLDER="TRUE"
NAME_FORMAT="{system}_{body}_{timestamp}"
NOTIFICATION_SOUND="$PROJECT_DIR/resources/Instant_Click.ogg"

# --- 4. Execution ---
log "INFO" "Executing EDScreenshot.py..."
log "INFO" "Monitoring Journal: $JOURNAL_FOLDER"

"$VENV_PATH/bin/python" -u "$PROJECT_DIR/EDScreenshot.py" \
    "$JOURNAL_FOLDER" \
    "$SCREENSHOT_FOLDER" \
    "$EXPORT_FORMAT" \
    "$CREATE_SYSTEM_FOLDER" \
    --name_format "$NAME_FORMAT" \
    --notification_sound "$NOTIFICATION_SOUND" 2>&1 | tee -a "$LOG_FILE"

# 5. Final Status
if [ ${PIPESTATUS[1]} -eq 0 ]; then
    log "SUCCESS" "Task completed successfully."
else
    log "ERROR" "Python script exited with an error."
fi
