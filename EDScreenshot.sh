#!/bin/bash

pip install -r requirements.txt

JOURNAL_FOLDER="YOUR JOURNAL FOLDER"
SCREENSHOT_FOLDER="THE ELITE DANGEROUS SCREENSHOT FOLDER"
EXPORT_FORMAT="PNG"
CREATE_SYSTEM_FOLDER="TRUE"

python EDScreenshot.py "$JOURNAL_FOLDER" "$SCREENSHOT_FOLDER" "$EXPORT_FORMAT" "$CREATE_SYSTEM_FOLDER"