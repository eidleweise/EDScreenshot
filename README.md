# EDScreenshot
![image](https://github.com/user-attachments/assets/5dcf828b-2886-4186-9e1e-441a1ff63aa0)

Just a quick python Script that I wrote to monitor the Elite Dangerous Journal file for a screenshot. Rename that Screenshot, convert it to a PNG and remove the original BMP

Oh! And because I am super lazy, I added the script to Lutris as a Linux "game"

* Game Options: `/usr/bin/ptyxis`
* Arguments: `-x ~/EDScreenshot/EDScreenshot.sh`

Hopefully it goes without saying that you'll need to update the shell script with your paths because you're not using mine :P

For what it's worth my copy of Elite is installed to `~/Games/umu/umu-default/drive_c/users/steamuser/Saved Games/Frontier Developments/Elite Dangerous`
 and my screenshots are in `~/Games/umu/umu-default/drive_c/users/steamuser/Pictures/Frontier Developments/Elite Dangerous`

## Optional Arguments

You can customize the behavior of EDScreenshot using optional command-line arguments:

### `--name_format <FORMAT>`
Customize the filename format for processed screenshots.

**Available placeholders:**
- `{system}` - Star system name
- `{body}` - Body name
- `{timestamp}` - Combined date+time as YYYYMMDD_HHMMSS
- `{date}` - Date as YYYY-MM-DD
- `{time}` - Time as HH-MM-SS
- `{datetime}` - Date and time as YYYY-MM-DD_HH-MM-SS

**Default:** `{system}_{body}_{timestamp}`

**Example:**
```bash
./EDScreenshot.sh --name_format "{system}_{body}_{timestamp}"
./EDScreenshot.sh --name_format "{datetime}_{body}"
```

### `--notification_sound <PATH>`
Play a sound file after processing a screenshot.

**Supported formats:** `.ogg`, `.wav`, `.mp3`

**Example:**
```bash
./EDScreenshot.sh --notification_sound "./resources/Instant_Click.ogg"
./EDScreenshot.sh --notification_sound "/path/to/custom/sound.wav"
```

If the sound file is not found or an unsupported format is used, the script will run silently with a warning.

## Environment Configuration

Edit the following variables in `EDScreenshot.sh` to customize paths and behavior:

- `JOURNAL_FOLDER` - Path to Elite Dangerous journal files
- `SCREENSHOT_FOLDER` - Path to Elite Dangerous screenshots
- `EXPORT_FORMAT` - Output format: `PNG`, `JPG`, or `JXL` (default: `PNG`)
- `CREATE_SYSTEM_FOLDER` - Organize screenshots by system folder: `TRUE` or `FALSE` (default: `TRUE`)
- `NOTIFICATION_SOUND` - Default notification sound file path

Eid
