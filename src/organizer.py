import os
import time
import json
import shutil
import hashlib
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
DOWNLOADS_DIR = os.path.expanduser("~/Downloads")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_FILE = os.path.expanduser("~/Library/Logs/mac-organizer.log")

# Setup logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(message)s')

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def get_category(extension, config):
    for category, extensions in config.items():
        if extension.lower() in extensions:
            return category
    return "Others"

def calculate_hash(filepath):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def is_duplicate(source_path, dest_path):
    """Check if source_path is a duplicate of dest_path."""
    if not os.path.exists(dest_path):
        return False
    
    # Check size first
    if os.path.getsize(source_path) != os.path.getsize(dest_path):
        return False
    
    # Check hash
    return calculate_hash(source_path) == calculate_hash(dest_path)

def get_unique_filename(dest_folder, filename):
    """Generate a unique filename if the file already exists."""
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(dest_folder, new_filename)):
        new_filename = f"{name} ({counter}){ext}"
        counter += 1
    return new_filename

class OrganizerHandler(FileSystemEventHandler):
    def __init__(self, config):
        self.config = config

    def on_created(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.process_file(event.dest_path)

    def process_file(self, filepath, wait_for_write=True):
        # Only process files directly in the Downloads folder
        if os.path.dirname(filepath) != DOWNLOADS_DIR:
            return

        # Ignore hidden files and temporary download files
        filename = os.path.basename(filepath)
        if filename.startswith('.') or filename.endswith('.download') or filename.endswith('.crdownload') or filename.endswith('.part'):
            return

        # Wait a moment to ensure file write is complete (simple heuristic)
        if wait_for_write:
            time.sleep(1)

        try:
            # Check if file still exists (it might have been moved/deleted rapidly)
            if not os.path.exists(filepath):
                return
            
            # Additional check to see if file is being written to? 
            # Often difficult to do perfectly without locking, but try reading size stable?
            # For now, rely on try/except move.

            extension = filename.split('.')[-1] if '.' in filename else ''
            category = get_category(extension, self.config)
            
            dest_folder = os.path.join(DOWNLOADS_DIR, category)
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)

            dest_path_initial = os.path.join(dest_folder, filename)

            # Check for duplicates
            # We need to check against ALL files in the destination folder? 
            # The requirement says "delete the duplicate file even if the name of files can be different"
            # So we strictly check if there is ANY file in dest_folder with same content.
            
            is_dup = False
            for existing_file in os.listdir(dest_folder):
                existing_filepath = os.path.join(dest_folder, existing_file)
                if os.path.isfile(existing_filepath):
                    if is_duplicate(filepath, existing_filepath):
                        logging.info(f"Duplicate found: {filename} is same as {existing_file}. Deleting new file.")
                        os.remove(filepath)
                        is_dup = True
                        break
            
            if is_dup:
                return

            # If not duplicate, determine final destination path (handle name collisions)
            final_filename = get_unique_filename(dest_folder, filename)
            final_dest_path = os.path.join(dest_folder, final_filename)
            
            shutil.move(filepath, final_dest_path)
            logging.info(f"Moved {filename} to {category}/{final_filename}")

        except Exception as e:
            logging.error(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    config = load_config()
    event_handler = OrganizerHandler(config)
    observer = Observer()
    observer.schedule(event_handler, DOWNLOADS_DIR, recursive=False)
    observer.start()
    logging.info(f"Started organizing {DOWNLOADS_DIR}")
    
    # Organize existing files on startup
    logging.info("Scanning existing files...")
    for filename in os.listdir(DOWNLOADS_DIR):
        filepath = os.path.join(DOWNLOADS_DIR, filename)
        if os.path.isfile(filepath):
             event_handler.process_file(filepath, wait_for_write=False)
    logging.info("Finished scanning existing files.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
