#!/bin/bash

# --- Configuration ---
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PATH="$PROJECT_DIR/.venv"
LOG_FILE="$PROJECT_DIR/ed_screenshot.log"

JOURNAL_FOLDER="/run/media/system/Games/WinePrefixes/elite-dangerous/drive_c/users/steamuser/Saved Games/Frontier Developments/Elite Dangerous/"
SCREENSHOT_FOLDER="/run/media/system/Games/WinePrefixes/elite-dangerous/drive_c/users/steamuser/Pictures/Frontier Developments/Elite Dangerous/"
EXPORT_FORMAT="PNG"
CREATE_SYSTEM_FOLDER="TRUE"
NAME_FORMAT="{system}_{body}_{timestamp}"
NOTIFICATION_SOUND="$PROJECT_DIR/resources/Instant_Click.ogg"

# --- Colors ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Logging ---
log() {
    local LEVEL=$1
    local MSG=$2
    local TIMESTAMP=$(date '+%H:%M:%S')

    case $LEVEL in
        "INFO")    echo -e "${BLUE}[$TIMESTAMP]${NC} $MSG" ;;
        "SUCCESS") echo -e "${GREEN}[$TIMESTAMP] $MSG${NC}" ;;
        "WARN")    echo -e "${YELLOW}[$TIMESTAMP] $MSG${NC}" ;;
        "ERROR")   echo -e "${RED}[$TIMESTAMP] ERROR: $MSG${NC}" ;;
    esac

    echo "[$TIMESTAMP] $LEVEL: $MSG" >> "$LOG_FILE"
}

# --- Virtual Environment ---
log "INFO" "Starting EDScreenshot..."

if [ -d "$VENV_PATH" ]; then
    "$VENV_PATH/bin/python" --version > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        log "WARN" "Virtual environment is corrupted. Recreating..."
        rm -rf "$VENV_PATH"
    fi
fi

if [ ! -d "$VENV_PATH" ]; then
    log "INFO" "Creating virtual environment..."
    python3 -m venv "$VENV_PATH" >> "$LOG_FILE" 2>&1
    if [ $? -ne 0 ]; then log "ERROR" "Failed to create venv"; exit 1; fi
fi

# --- Dependencies ---
log "INFO" "Checking dependencies..."
"$VENV_PATH/bin/pip" install -q -r "$PROJECT_DIR/requirements.txt" >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "SUCCESS" "Environment ready."
else
    log "ERROR" "Pip install failed. Check $LOG_FILE"
    exit 1
fi

# --- Run ---
log "INFO" "Monitoring: $JOURNAL_FOLDER"

"$VENV_PATH/bin/python" -u "$PROJECT_DIR/EDScreenshot.py" \
    "$JOURNAL_FOLDER" \
    "$SCREENSHOT_FOLDER" \
    "$EXPORT_FORMAT" \
    "$CREATE_SYSTEM_FOLDER" \
    --name_format "$NAME_FORMAT" \
    --notification_sound "$NOTIFICATION_SOUND" 2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    log "SUCCESS" "Task completed successfully."
else
    log "ERROR" "Python script exited with an error."
fi
