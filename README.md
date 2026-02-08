# Mac Organizer

A background utility for macOS that automatically keeps your `~/Downloads` folder organized.

## 1. What is this tool?

**Mac Organizer** is a lightweight Python script that runs silently in the background. It monitors your Downloads folder in real-time and:

*   **Categorizes Files**: Automatically moves files into subfolders (e.g., `Images`, `Documents`, `Archives`) based on their file extensions.
*   **Cleans Up Duplicates**: Detects if you download the same file twice (even with a different name) and deletes the duplicate to save space.
*   **Smart Archival**:
    **How it works:**
    1.  **Monitors Age:** It checks the "**Date Modified**" of files.
    2.  **Auto-Archive:** If a file hasn't been modified for **5 days**, it moves it into `archive.zip`. It works recursively, so even subfolders get their own tidy `archive.zip`.
*   **Startup Scan**: When you log in or start the service, it instantly organizes any existing files in the folder.

## 2. How the Code Works

The project relies on a few key components:

### The Core: `watchdog` Library
We use the python `watchdog` library to listen for file system events. Instead of constantly checking the folder (polling), which wastes resources, `watchdog` asks the OS to notify our script only when a file is created or moved.

### Code Walkthrough (`src/organizer.py`)

*   **`OrganizerHandler` Class**: This is the heart of the script. It inherits from `FileSystemEventHandler`.
    *   `on_created` & `on_moved`: These methods are triggered by the OS. We filter out temporary files (like `.crdownload` from Chrome) and then call `process_file`.
*   **`process_file(filepath)`**:
    1.  **Checks Extension**: Reads `src/config.json` to decide where the file goes.
    2.  **Duplicate Check**: Before moving, it checks the destination folder. It compares **File Size** and **SHA256 Hash** (digital fingerprint) to ensure files are truly identical. If it's a duplicate, it deletes the new file.
    3.  **Move**: If unique, it uses `shutil.move` to place the file in its category folder.
*   **Startup Logic**: At the bottom of the script, before starting the observer loop, we iterate through all existing files in `Downloads` to organize them immediately.

### Configuration (`src/config.json`)
You can specify **one or multiple** folders to organize:
```json
{
  "target_directories": [
    "~/Downloads",
    "~/Desktop/Screenshots",
    "~/Documents/Unsorted"
  ],
  "archive": {
    "enabled": true,
    "days": 5
  },
  "Images": ["jpg", "png", "gif"],
  "Documents": ["pdf", "docx", "txt"]
}
```
*   **archive**: Set `enabled` to `true` to turn on auto-archiving. `days` sets the age threshold (files older than this are moved to `archive.zip`).

### Background Service (`com.user.macorganizer.plist`)
This is a standard macOS **Launch Agent** file. It tells macOS to:
*   Start our python script automatically when you log in.
*   Restart it if it crashes (`KeepAlive`).
*   Save logs to `~/Library/Logs/mac-organizer.log`.

## 3. Setup & Installation

The tool is designed to run in a Python virtual environment to avoid messaging up your system python.

**Prerequisites:** Python 3 installed.

**Installation Steps:**
1.  Clone the repository and enter the directory:
    ```bash
    git clone [https://github.com/yourusername/mac-organizer.git](https://github.com/allen-turing/mac-organizer.git)
    cd mac-organizer
    ```
2.  Run the installation script:
    ```bash
    chmod +x install.sh
    ./install.sh
    ```
    This script will automatically:
    *   Create a virtual environment.
    *   Install dependencies (`watchdog`).
    *   Configure and start the background service.

**Uninstallation:**
To remove the tool and stop the service:
```bash
./uninstall.sh
```

## 4. Managing the Organization

You don't need to do anything! Just download files.

**Control Commands:**
*   **Check Setup**: `launchctl list | grep macorganizer`
*   **Stop**: `launchctl unload ~/Library/LaunchAgents/com.user.macorganizer.plist`
*   **Start**: `launchctl load ~/Library/LaunchAgents/com.user.macorganizer.plist`
*   **View Logs**: `tail -f ~/Library/Logs/mac-organizer.log`

## 5. Development & Updates

If you change `config.json` or modify the Python code:

1.  Make your changes.
2.  Run the reload script to apply them:
    ```bash
    ./reload.sh
    ```

