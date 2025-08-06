import argparse
import os
import sys
import time
import glob
import json
import shutil
from datetime import datetime, timedelta
from PIL import Image
import threading
import queue
import pillow_jxl


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


def process_journal_thread(journal_queue, screenshot_path, export_format="PNG", create_system_folder=True, interval=1):
    current_journal = None
    last_line = None
    while True:
        try:
            journal_file = journal_queue.get(block=False)
            if journal_file is not None:
                current_journal = journal_file
                print(f"Monitoring {current_journal}")
                last_line = None  # reset when new file is passed.
        except queue.Empty:
            pass  # No new journal, continue processing current

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
                                    process_screenshot(screenshot_path, journal_data, create_system_folder,
                                                       export_format)
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


def process_screenshot(elite_screenshot_input_path, journal_entry, make_system_name=True, output_format="PNG"):
    output_format = output_format.upper()  # Normalize to uppercase
    try:
        if journal_entry["event"] == "Screenshot":
            image_name = journal_entry["Filename"]
            image_name = os.path.abspath(image_name.replace("\\", os.path.sep))
            image_file_name = os.path.basename(image_name)
            abs_image_file_name = os.path.join(elite_screenshot_input_path, image_file_name)
            system = journal_entry.get("System", "UnknownSystem").replace(":", "-")
            body = journal_entry.get("Body", "UnknownBody").replace(":", "-")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{system}_{body}_{timestamp}.bmp"

            if make_system_name:
                new_abs_bmp_file_name = os.path.join(elite_screenshot_input_path, system, new_filename)
            else:
                new_abs_bmp_file_name = os.path.join(elite_screenshot_input_path, new_filename)

            os.makedirs(os.path.dirname(new_abs_bmp_file_name), exist_ok=True)
            shutil.move(str(abs_image_file_name), new_abs_bmp_file_name)
            print(f"Screenshot renamed to: {new_abs_bmp_file_name}")

            if output_format == "PNG":
                bmp_to_png(new_abs_bmp_file_name, True)
            elif output_format == "JPG":
                bmp_to_jpg(new_abs_bmp_file_name, True)
            elif output_format == "JXL":
                bmp_to_jxl(new_abs_bmp_file_name, True, True)
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


if __name__ == "__main__":
    lock_file_name = f"EDScreenshot.lock"
    max_lock_age_seconds = 24 * 60 * 60  # 24 hours in seconds

    if os.path.exists(lock_file_name):
        try:
            print(f"Lock file '{lock_file_name}' exists. This may mean another instance is running.")
            choice = input("Do you want to remove it and continue? (y/n): ").lower().strip()

            if choice == 'y':
                os.remove(lock_file_name)
                print("Lock file removed. Continuing.")
            else:
                print("Exiting.")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\nOperation cancelled. Exiting.")
            sys.exit(1)
        except OSError as e:
            print(f"Error accessing or deleting lock file '{lock_file_name}': {e}")
            sys.exit(1)
    else:
        # Lock file does not exist, continue with your script
        print(f"Lock file '{lock_file_name}' does not exist. Continuing execution.")
        # You would typically create the lock file here before critical sections
        with open(lock_file_name, "w") as f:
            f.write(str(os.getpid()))  # Optionally write the process ID to the lock file

    parser = argparse.ArgumentParser(description="Monitor Elite Dangerous journal files and process screenshots.")
    parser.add_argument("journal_folder", help="Path to the Elite Dangerous journal folder.")
    parser.add_argument("screenshot_folder", help="Path to the Elite Dangerous screenshot folder.")
    parser.add_argument("export_format", nargs='?', default="PNG", help="Export as PNG (default), JPG or JXL")
    parser.add_argument("create_system_folder", nargs='?', type=lambda x: (str(x).lower() == 'true'), default=True,
                        help="Rather than exporting in the image to the main Elite Dangerous images folder, export them to image_folder/system_name (True/False)")

    args = parser.parse_args()

    print("Parsed Arguments:")
    for arg_name, arg_value in vars(args).items():
        print(f"\t{arg_name}: {arg_value}")

    folder_to_monitor = args.journal_folder
    elite_screenshot_path = args.screenshot_folder
    export_format = args.export_format
    create_system_folder = args.create_system_folder

    journal_queue = queue.Queue()

    folder_thread = threading.Thread(target=monitor_folder_thread, args=(folder_to_monitor, journal_queue))
    process_thread = threading.Thread(target=process_journal_thread,
                                      args=(journal_queue, elite_screenshot_path, export_format, create_system_folder))

    folder_thread.daemon = True
    process_thread.daemon = True

    folder_thread.start()
    process_thread.start()

    try:
        while True:
            time.sleep(1)  # main thread does minimal work.
    except KeyboardInterrupt:
        try:
            os.remove(lock_file_name)
            print("\nMonitoring stopped.")
        except OSError as e:
            print(f"Error accessing or deleting lock file '{lock_file_name}': {e}")
