import os
import time
import json
import shutil
import hashlib
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
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
    def __init__(self, config, target_directories):
        self.config = config
        self.target_directories = target_directories

    def on_created(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.process_file(event.dest_path)

    def process_file(self, filepath, wait_for_write=True):
        # Only process files directly in one of the Target folders
        # Helper to check if file is directly in ONE of the target_directories
        file_dir = os.path.dirname(filepath)
        if file_dir not in self.target_directories:
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
            
            # Use the directory the file is currently IN as the base for destination
            # This ensures if we are watching ~/Desktop, it moves to ~/Desktop/Images
            dest_folder = os.path.join(file_dir, category)
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
    
    # support legacy target_directory string or new list
    targets = config.get("target_directories", [])
    if "target_directory" in config:
        targets.append(config["target_directory"])
    
    # Expand user paths and deduplicate
    target_dirs = list(set([os.path.expanduser(t) for t in targets]))
    
    if not target_dirs:
        # Default to Downloads if nothing specified
        target_dirs = [os.path.expanduser("~/Downloads")]

    valid_targets = []
    for t in target_dirs:
        if os.path.exists(t):
            valid_targets.append(t)
        else:
            logging.warning(f"Target directory {t} does not exist. Skipping.")
    
    if not valid_targets:
        logging.error("No valid target directories found.")
        exit(1)

    event_handler = OrganizerHandler(config, valid_targets)
    observer = Observer()
    
    for target_dir in valid_targets:
        observer.schedule(event_handler, target_dir, recursive=False)
        logging.info(f"Started organizing {target_dir}")
    
    observer.start()
    
    # Organize existing files on startup for ALL targets
    logging.info("Scanning existing files...")
    for target_dir in valid_targets:
        logging.info(f"Scanning {target_dir}...")
        for filename in os.listdir(target_dir):
            filepath = os.path.join(target_dir, filename)
            if os.path.isfile(filepath):
                 event_handler.process_file(filepath, wait_for_write=False)
    logging.info("Finished scanning existing files.")

    # Periodic Archival
    if config.get("archive", {}).get("enabled", False):
        days = config["archive"].get("days", 5)
        logging.info(f"Archival enabled: checking for files older than {days} days every 24 hours.")
        
        import threading

        def run_archival():
            logging.info("Starting archival process...")
            threshold_seconds = days * 86400
            current_time = time.time()

            for target_dir in valid_targets:
                logging.info(f"Archiving in {target_dir}...")
                
                # Iterate over subdirectories in Target Directory
                for item in os.listdir(target_dir):
                    item_path = os.path.join(target_dir, item)
                    
                    # Only look inside directories (e.g. Images, Documents)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        
                        # Walk through all subdirectories recursively
                        for root, dirs, files in os.walk(item_path):
                            archive_path = os.path.join(root, "archive.zip")
                            files_to_archive = []

                            # Find candidates in the current 'root' folder
                            for filename in files:
                                filepath = os.path.join(root, filename)
                                # Skip archive.zip itself and hidden files
                                if filename == "archive.zip" or filename.startswith('.'):
                                    continue
                                
                                if os.path.isfile(filepath):
                                    try:
                                        file_mtime = os.path.getmtime(filepath)
                                        if (current_time - file_mtime) > threshold_seconds:
                                            files_to_archive.append(filename)
                                    except OSError:
                                        continue # Skip files if there's an error accessing attributes
                            
                            if files_to_archive:
                                logging.info(f"Archiving {len(files_to_archive)} files in {root}...")
                                import zipfile
                                try:
                                    # Append to zip
                                    with zipfile.ZipFile(archive_path, 'a', zipfile.ZIP_DEFLATED) as zipf:
                                        for file in files_to_archive:
                                            file_path = os.path.join(root, file)
                                            # Write file to zip with just the filename (no path structure inside zip)
                                            zipf.write(file_path, file)
                                            logging.info(f"Archived {file}")
                                    
                                    # Delete original files
                                    for file in files_to_archive:
                                        file_path = os.path.join(root, file)
                                        os.remove(file_path)
                                        logging.info(f"Deleted original {file}")
                                        
                                except Exception as e:
                                    logging.error(f"Failed to archive in {root}: {e}")

            logging.info("Archival process finished.")
            # Schedule next run in 24 hours
            threading.Timer(86400, run_archival).start()

        # Run immediately on startup (in a separate thread to not block observer)
        threading.Thread(target=run_archival).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
