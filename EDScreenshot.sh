#!/bin/bash
#
# EDScreenshot - Elite Dangerous Screenshot Monitor
#
# This script monitors Elite Dangerous journal files and automatically processes screenshots.
# It sets up a Python virtual environment and runs the EDScreenshot.py monitoring service.
#
# USAGE:
#   ./EDScreenshot.sh                                       # Run with default configuration
#   ./EDScreenshot.sh --name_format "{system}_{timestamp}"  # Custom filename format
#   ./EDScreenshot.sh --notification_sound /path/to/sound   # Custom notification sound
#
# OPTIONAL ARGUMENTS:
#
#   --name_format <FORMAT>
#       Filename format template for processed screenshots.
#       Available placeholders:
#         {system}    - Star system name
#         {body}      - Body name
#         {timestamp} - Combined date+time as YYYYMMDD_HHMMSS
#         {date}      - Date as YYYY-MM-DD
#         {time}      - Time as HH-MM-SS
#         {datetime}  - Date and time as YYYY-MM-DD_HH-MM-SS
#       Default: "{system}_{body}_{timestamp}"
#       Example: --name_format "{system}_{body}_{timestamp}"
#
#   --notification_sound <PATH>
#       Path to a sound file to play after processing a screenshot.
#       Supported formats: .ogg, .wav, .mp3
#       If not provided, no sound will be played after screenshots are processed.
#       Example: --notification_sound "/path/to/sound.ogg"
#
# ENVIRONMENT CONFIGURATION:
#
#   The following variables can be edited in this script for custom configuration:
#
#     JOURNAL_FOLDER         - Path to Elite Dangerous journal files
#     SCREENSHOT_FOLDER      - Path to Elite Dangerous screenshots
#     EXPORT_FORMAT          - Output format: PNG, JPG, or JXL (default: PNG)
#     CREATE_SYSTEM_FOLDER   - Organize screenshots by system folder (default: TRUE)
#
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
