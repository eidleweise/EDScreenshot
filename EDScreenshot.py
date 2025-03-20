import argparse
import os
import time
import glob
import json
import shutil
from datetime import datetime
from PIL import Image
import threading
import queue

def get_latest_log_file(folder_path):
    log_files = glob.glob(os.path.join(folder_path, "*.log"))
    if not log_files:
        return None
    latest_file = max(log_files, key=os.path.getmtime)
    return latest_file

def monitor_folder_thread(folder_path, journal_queue, interval=5):
    most_recent_logfile = None
    while True:
        latest_log = get_latest_log_file(folder_path)
        if latest_log:
            if latest_log != most_recent_logfile:
                most_recent_logfile = latest_log
                journal_queue.put(most_recent_logfile)
        else:
            if most_recent_logfile is not None:
                most_recent_logfile = None
                journal_queue.put(None)
        time.sleep(interval)

def process_journal_thread(journal_queue, screenshot_path, interval=1):
    current_journal = None
    last_line = None
    while True:
        try:
            journal_file = journal_queue.get(block=False)
            if journal_file is not None:
                current_journal = journal_file
                print(f"Monitoring {current_journal}")
                last_line = None #reset when new file is passed.
        except queue.Empty:
            pass # No new journal, continue processing current

        if current_journal:
            try:
                with open(current_journal, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        current_last_line = lines[-1].strip()
                        if current_last_line != last_line:
                            last_line = current_last_line
                            try:
                                journal_data = json.loads(current_last_line)
                                if journal_data["event"] == "Screenshot":
                                    process_screenshot(screenshot_path, journal_data)
                            except json.JSONDecodeError:
                                pass
                            except Exception as e:
                                print(f"Error processing journal line: {e}")
            except FileNotFoundError:
                print(f"Journal file not found: {current_journal}")
            except PermissionError:
                print(f"Permission denied to read journal file: {current_journal}")
            except Exception as e:
                print(f"Error reading journal: {e}")
        time.sleep(interval)

def process_screenshot(elite_screenshot_path, journal_entry):
    try:
        if journal_entry["event"] == "Screenshot":
            image_name = journal_entry["Filename"]
            image_name = os.path.abspath(image_name.replace("\\", os.path.sep))
            image_file_name = os.path.basename(image_name)
            abs_image_file_name = os.path.join(elite_screenshot_path, image_file_name)
            system = journal_entry.get("System", "UnknownSystem").replace(":", "-")
            body = journal_entry.get("Body", "UnknownBody").replace(":", "-")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{system}_{body}_{timestamp}.bmp"
            new_abs_image_file_name = os.path.join(elite_screenshot_path, new_filename)
            shutil.move(str(abs_image_file_name), new_abs_image_file_name)
            print(f"Screenshot renamed to: {new_abs_image_file_name}")
            bmp_to_png(new_abs_image_file_name)
    except KeyError:
        print("Incomplete screenshot journal entry.")
    except FileNotFoundError:
        print(f"Screenshot file not found: {image_name}")
    except Exception as e:
        print(f"Error processing screenshot: {e}")

def bmp_to_png(bmp_path):
    try:
        img = Image.open(bmp_path)
        png_path = os.path.splitext(bmp_path)[0] + ".png"
        img.save(png_path, "PNG")
        print(f"Converted to PNG: {png_path}")
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor Elite Dangerous journal files and process screenshots.")
    parser.add_argument("journal_folder", help="Path to the Elite Dangerous journal folder.")
    parser.add_argument("screenshot_folder", help="Path to the Elite Dangerous screenshot folder.")
    args = parser.parse_args()

    folder_to_monitor = args.journal_folder
    elite_screenshot_path = args.screenshot_folder

    journal_queue = queue.Queue()

    folder_thread = threading.Thread(target=monitor_folder_thread, args=(folder_to_monitor, journal_queue))
    process_thread = threading.Thread(target=process_journal_thread, args=(journal_queue, elite_screenshot_path))

    folder_thread.daemon = True
    process_thread.daemon = True

    folder_thread.start()
    process_thread.start()

    try:
        while True:
            time.sleep(1) #main thread does minimal work.
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")