import argparse
import os
import sys
import time
import glob
import json
import shutil
from datetime import datetime
from PIL import Image
import threading
import pillow_jxl
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    import pygame
    pygame.mixer.init()
    _SOUND_AVAILABLE = True
except (ImportError, pygame.error):
    _SOUND_AVAILABLE = False

_SUPPORTED_SOUND_FORMATS = ('.ogg', '.wav', '.mp3')
_NOTIFICATION_COOLDOWN = 2.0  # seconds — suppress repeated sounds within this window
_last_notification_time = 0.0
_notification_sound_path = None  # Set from CLI argument


def play_notification():
    """Play the notification sound in a background thread, debounced to avoid spam."""
    global _last_notification_time

    if not _SOUND_AVAILABLE or not _notification_sound_path:
        return

    now = time.time()
    if now - _last_notification_time < _NOTIFICATION_COOLDOWN:
        return
    _last_notification_time = now

    def _play():
        try:
            sound = pygame.mixer.Sound(_notification_sound_path)
            sound.play()
            while pygame.mixer.get_busy():
                time.sleep(0.05)
        except Exception as e:
            print(f"Error playing notification sound: {e}")

    threading.Thread(target=_play, daemon=True).start()


def get_latest_log_file(folder_path):
    log_files = glob.glob(os.path.join(folder_path, "*.log"))
    if not log_files:
        return None
    latest_file = max(log_files, key=os.path.getmtime)
    return latest_file


class JournalHandler(FileSystemEventHandler):
    """Watches the journal folder and tails new lines from the latest log file."""

    def __init__(self, screenshot_path, export_format, create_system_folder, name_format):
        super().__init__()
        self.screenshot_path = screenshot_path
        self.export_format = export_format
        self.create_system_folder = create_system_folder
        self.name_format = name_format
        self.current_journal = None
        self.file_position = 0
        self._lock = threading.Lock()

    def start(self, journal_folder):
        """Seek to end of the current latest journal so we only process new events."""
        latest = get_latest_log_file(journal_folder)
        if latest:
            self.current_journal = latest
            self.file_position = os.path.getsize(latest)
            print(f"Monitoring {self.current_journal} (tailing from end)")

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.log'):
            return
        with self._lock:
            self._process_changes(event.src_path)

    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.log'):
            return
        with self._lock:
            # New journal file started — switch to it
            self.current_journal = event.src_path
            self.file_position = 0
            print(f"New journal detected: {self.current_journal}")
            self._process_changes(event.src_path)

    def _process_changes(self, changed_path):
        # Only process the current (latest) journal
        if self.current_journal is None:
            self.current_journal = changed_path
            self.file_position = 0

        # If a newer journal appeared via modification, switch to it
        if changed_path != self.current_journal:
            if os.path.getmtime(changed_path) > os.path.getmtime(self.current_journal):
                self.current_journal = changed_path
                self.file_position = 0
                print(f"Switched to newer journal: {self.current_journal}")

        if changed_path != self.current_journal:
            return

        try:
            with open(self.current_journal, 'r', encoding='utf-8') as f:
                f.seek(self.file_position)
                new_lines = f.readlines()
                self.file_position = f.tell()

            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    journal_data = json.loads(line)
                    if journal_data.get("event") == "Screenshot":
                        process_screenshot(self.screenshot_path, journal_data,
                                           self.create_system_folder, self.export_format,
                                           self.name_format)
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Error processing journal line: {e}")

        except FileNotFoundError:
            print(f"Journal file not found: {self.current_journal}")
        except PermissionError:
            print(f"Permission denied: {self.current_journal}")
        except Exception as e:
            print(f"Error reading journal: {e}")


def build_filename(name_format, journal_entry):
    """Build a filename from a format string and journal entry data.

    Available placeholders:
        {system}    - Star system name
        {body}      - Body name
        {timestamp} - Combined date+time as YYYYMMDD_HHMMSS
        {date}      - Date as YYYY-MM-DD
        {time}      - Time as HH-MM-SS
        {datetime}  - Date and time as YYYY-MM-DD_HH-MM-SS
    """
    now = datetime.now()
    system = journal_entry.get("System", "UnknownSystem").replace(":", "-")
    body = journal_entry.get("Body", "UnknownBody").replace(":", "-")

    replacements = {
        "system": system,
        "body": body,
        "timestamp": now.strftime("%Y%m%d_%H%M%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H-%M-%S"),
        "datetime": now.strftime("%Y-%m-%d_%H-%M-%S"),
    }

    try:
        return name_format.format(**replacements)
    except KeyError as e:
        print(f"Unknown placeholder in name format: {e}. Using default.")
        return f"{system}_{body}_{replacements['timestamp']}"


def process_screenshot(elite_screenshot_input_path, journal_entry, make_system_name=True, output_format="PNG",
                       name_format="{system}_{body}_{timestamp}"):
    output_format = output_format.upper()  # Normalize to uppercase
    try:
        if journal_entry["event"] == "Screenshot":
            image_name = journal_entry["Filename"]
            image_name = os.path.abspath(image_name.replace("\\", os.path.sep))
            image_file_name = os.path.basename(image_name)
            abs_image_file_name = os.path.join(elite_screenshot_input_path, image_file_name)
            system = journal_entry.get("System", "UnknownSystem").replace(":", "-")

            new_filename = build_filename(name_format, journal_entry) + ".bmp"

            if make_system_name:
                new_abs_bmp_file_name = os.path.join(elite_screenshot_input_path, system, new_filename)
            else:
                new_abs_bmp_file_name = os.path.join(elite_screenshot_input_path, new_filename)

            os.makedirs(os.path.dirname(new_abs_bmp_file_name), exist_ok=True)
            shutil.move(str(abs_image_file_name), new_abs_bmp_file_name)
            print(f"Screenshot renamed to: {new_abs_bmp_file_name}")

            if output_format == "PNG":
                bmp_to_png(new_abs_bmp_file_name, True)
                play_notification()
            elif output_format == "JPG":
                bmp_to_jpg(new_abs_bmp_file_name, True)
                play_notification()
            elif output_format == "JXL":
                bmp_to_jxl(new_abs_bmp_file_name, True, True)
                play_notification()
            else:
                print(f"Unknown output format {output_format}")
    except KeyError:
        print("Incomplete screenshot journal entry.")
    except FileNotFoundError as fnfe:
        print(f"Screenshot file not found: {image_name} : {fnfe}")
    except Exception as e:
        print(f"Error processing screenshot: {e}")


def bmp_to_png(bmp_path, delete_original=True):
    try:
        img = Image.open(bmp_path)
        png_path = os.path.splitext(bmp_path)[0] + ".png"
        img.save(png_path, "PNG")
        print(f"Converted to PNG: {png_path}")
        if delete_original:
            os.remove(bmp_path)
        return png_path
    except FileNotFoundError:
        print(f"Error: File '{bmp_path}' not found.")
    except PermissionError:
        print(f"Error: Permission denied to delete '{bmp_path}'.")
    except OSError as e:  # Catch other OS related errors.
        print(f"Error deleting file: {e}")
    except Exception as e:
        print(f"Error converting BMP to PNG: {e}")
        return None


def bmp_to_jpg(bmp_path, delete_original=True):
    try:
        img = Image.open(bmp_path)
        jpg_path = os.path.splitext(bmp_path)[0] + ".jpg"
        img.save(jpg_path, "JPEG")
        print(f"Converted to PNG: {jpg_path}")
        if delete_original:
            os.remove(bmp_path)
        return jpg_path
    except FileNotFoundError:
        print(f"Error: File '{bmp_path}' not found.")
    except PermissionError:
        print(f"Error: Permission denied to delete '{bmp_path}'.")
    except OSError as e:  # Catch other OS related errors.
        print(f"Error deleting file: {e}")
    except Exception as e:
        print(f"Error converting BMP to JPG: {e}")
        return None


def bmp_to_jxl(bmp_path, delete_original=True, lossless_val=True):
    try:
        img = Image.open(bmp_path)
        jxl_path = os.path.splitext(bmp_path)[0] + ".jxl"
        img.save(jxl_path, "JXL", lossless=lossless_val)
        print(f"Converted to JXL: {jxl_path}")
        if delete_original:
            os.remove(bmp_path)
        return jxl_path
    except FileNotFoundError:
        print(f"Error: File '{bmp_path}' not found.")
    except PermissionError:
        print(f"Error: Permission denied to delete '{bmp_path}'.")
    except OSError as e:  # Catch other OS related errors.
        print(f"Error deleting file: {e}")
    except Exception as e:
        print(f"Error converting BMP to JXL: {e}")
        return None


def is_pid_alive(pid):
    """Check whether a process with the given PID is still running (cross-platform)."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)  # Signal 0: no kill, just check existence
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we don't have permission to signal it — still alive
        return True
    return True


def acquire_lock(lock_path):
    """Acquire a PID-based lock file. Returns True if lock acquired, False if another instance is running."""
    if os.path.exists(lock_path):
        try:
            with open(lock_path, "r") as f:
                old_pid = int(f.read().strip())
        except (ValueError, OSError):
            old_pid = -1

        if is_pid_alive(old_pid):
            return False  # Another instance is genuinely running

        # Stale lock from a dead process — reclaim it
        print(f"Removing stale lock file (PID {old_pid} is no longer running).")

    with open(lock_path, "w") as f:
        f.write(str(os.getpid()))
    return True


def release_lock(lock_path):
    """Remove the lock file if it belongs to us."""
    try:
        with open(lock_path, "r") as f:
            pid = int(f.read().strip())
        if pid == os.getpid():
            os.remove(lock_path)
    except (ValueError, OSError):
        pass


if __name__ == "__main__":
    lock_file_name = "EDScreenshot.lock"

    if not acquire_lock(lock_file_name):
        print("Another instance is already running. Exiting.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Monitor Elite Dangerous journal files and process screenshots.")
    parser.add_argument("journal_folder", help="Path to the Elite Dangerous journal folder.")
    parser.add_argument("screenshot_folder", help="Path to the Elite Dangerous screenshot folder.")
    parser.add_argument("export_format", nargs='?', default="PNG", help="Export as PNG (default), JPG or JXL")
    parser.add_argument("create_system_folder", nargs='?', type=lambda x: (str(x).lower() == 'true'), default=True,
                        help="Rather than exporting in the image to the main Elite Dangerous images folder, export them to image_folder/system_name (True/False)")
    parser.add_argument("--name_format", default="{system}_{body}_{timestamp}",
                        help="Filename format template. Available placeholders: "
                             "{system}, {body}, {timestamp}, {date}, {time}, {datetime}. "
                             "Default: '{system}_{body}_{timestamp}'")
    parser.add_argument("--notification_sound", default=None,
                        help="Path to a sound file (.ogg, .wav, .mp3) to play after processing. "
                             "If not provided, no sound is played.")

    args = parser.parse_args()

    # Validate and set notification sound
    if args.notification_sound:
        sound_path = os.path.abspath(args.notification_sound)
        if not os.path.exists(sound_path):
            print(f"Warning: Notification sound not found: {sound_path} — running silent.")
        elif not sound_path.lower().endswith(_SUPPORTED_SOUND_FORMATS):
            print(f"Warning: Unsupported sound format. Use .ogg, .wav, or .mp3 — running silent.")
        else:
            _notification_sound_path = sound_path

    print("Parsed Arguments:")
    for arg_name, arg_value in vars(args).items():
        print(f"\t{arg_name}: {arg_value}")

    journal_folder = args.journal_folder
    screenshot_path = args.screenshot_folder
    export_format = args.export_format
    create_system_folder = args.create_system_folder
    name_format = args.name_format

    if not os.path.isdir(journal_folder):
        print(f"Error: Journal folder does not exist: {journal_folder}")
        release_lock(lock_file_name)
        sys.exit(1)

    handler = JournalHandler(screenshot_path, export_format, create_system_folder, name_format)
    handler.start(journal_folder)

    observer = Observer()
    observer.schedule(handler, journal_folder, recursive=False)
    observer.start()
    print(f"Watching journal folder: {journal_folder}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
        release_lock(lock_file_name)
        print("\nMonitoring stopped.")
