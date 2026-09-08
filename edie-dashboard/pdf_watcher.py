"""
E.D.I.E. Local PDF Watcher
==========================
Watches a local folder for new PDF files and auto-uploads them to
Snowflake stage @INSURANCE_AI_HUB.ANALYTICS.PDF_INTAKE_STAGE
for automatic ingestion by the AUTO_INGEST_PDF_TASK.

Setup:
  1. pip install snowflake-connector-python watchdog
  2. Edit the CONFIG section below with your Snowflake credentials
  3. Create the watch folder (default: ~/PolicyPDFs)
  4. Run: python pdf_watcher.py
  5. Drop PDFs into the folder — they auto-upload within seconds

Usage:
  python pdf_watcher.py                          # Watch default folder
  python pdf_watcher.py --folder /path/to/folder  # Watch custom folder
  python pdf_watcher.py --once                    # Upload existing files and exit
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path

# ============================================================
# CONFIG — Edit these with your Snowflake credentials
# ============================================================
SNOWFLAKE_CONFIG = {
    "account": "rj88085",           # Your Snowflake account
    "user": "RONAK67",              # Your username
    "password": "",                 # Fill in, or use authenticator below
    "authenticator": "externalbrowser",  # Opens browser for SSO login (remove password if using this)
    "warehouse": "COMPUTE_WH",
    "database": "INSURANCE_AI_HUB",
    "schema": "ANALYTICS",
    "role": "ACCOUNTADMIN",
}

STAGE = "@INSURANCE_AI_HUB.ANALYTICS.PDF_INTAKE_STAGE"
DEFAULT_WATCH_FOLDER = r"C:\Users\u522055\Desktop\PDFS"
PROCESSED_FOLDER = "processed"  # Subfolder to move files after upload

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("pdf_watcher")

# ============================================================
# SNOWFLAKE UPLOAD
# ============================================================
def get_connection():
    import snowflake.connector
    config = {k: v for k, v in SNOWFLAKE_CONFIG.items() if v}
    conn = snowflake.connector.connect(**config)
    log.info(f"Connected to Snowflake as {SNOWFLAKE_CONFIG['user']}@{SNOWFLAKE_CONFIG['account']}")
    return conn


def upload_pdf(conn, file_path):
    """Upload a single PDF to the Snowflake stage."""
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path) / 1024  # KB

    log.info(f"Uploading: {file_name} ({file_size:.1f} KB)")

    cursor = conn.cursor()
    try:
        # Clean any existing file with same name
        cursor.execute(f"REMOVE {STAGE}/{file_name}")
    except Exception:
        pass

    try:
        # Upload to stage
        cursor.execute(
            f"PUT 'file://{file_path}' {STAGE}/{file_name}/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        )
        result = cursor.fetchone()
        status = result[6] if result else "UNKNOWN"  # status column

        if status in ("UPLOADED", "SKIPPED"):
            log.info(f"Uploaded: {file_name} -> {STAGE}/{file_name}/ (status: {status})")
            return True
        else:
            log.error(f"Upload failed for {file_name}: {status}")
            return False
    except Exception as e:
        log.error(f"Upload error for {file_name}: {e}")
        return False
    finally:
        cursor.close()


def move_to_processed(file_path, watch_folder):
    """Move uploaded file to processed subfolder."""
    processed_dir = os.path.join(watch_folder, PROCESSED_FOLDER)
    os.makedirs(processed_dir, exist_ok=True)
    dest = os.path.join(processed_dir, os.path.basename(file_path))

    # Handle duplicate names
    if os.path.exists(dest):
        name, ext = os.path.splitext(os.path.basename(file_path))
        dest = os.path.join(processed_dir, f"{name}_{int(time.time())}{ext}")

    os.rename(file_path, dest)
    log.info(f"Moved to: {dest}")


# ============================================================
# FOLDER WATCHER
# ============================================================
def process_existing_files(conn, watch_folder):
    """Upload any PDFs already in the folder."""
    count = 0
    for f in sorted(os.listdir(watch_folder)):
        if f.lower().endswith(".pdf") and not f.startswith("."):
            file_path = os.path.join(watch_folder, f)
            if os.path.isfile(file_path):
                if upload_pdf(conn, file_path):
                    move_to_processed(file_path, watch_folder)
                    count += 1
    return count


def watch_folder_polling(conn, watch_folder, interval=5):
    """Simple polling-based watcher (no extra dependencies needed)."""
    log.info(f"Watching folder: {watch_folder}")
    log.info(f"Polling every {interval} seconds. Press Ctrl+C to stop.")
    log.info(f"Drop PDF files into this folder to auto-upload to Snowflake.\n")

    seen_files = set()

    # Track existing files
    for f in os.listdir(watch_folder):
        if f.lower().endswith(".pdf"):
            seen_files.add(f)

    try:
        while True:
            time.sleep(interval)

            current_files = set()
            for f in os.listdir(watch_folder):
                if f.lower().endswith(".pdf") and not f.startswith("."):
                    fp = os.path.join(watch_folder, f)
                    if os.path.isfile(fp):
                        current_files.add(f)

            new_files = current_files - seen_files
            for f in sorted(new_files):
                file_path = os.path.join(watch_folder, f)
                # Wait a moment for file to finish writing
                time.sleep(1)
                if upload_pdf(conn, file_path):
                    move_to_processed(file_path, watch_folder)

            seen_files = set()
            for f in os.listdir(watch_folder):
                if f.lower().endswith(".pdf"):
                    seen_files.add(f)

    except KeyboardInterrupt:
        log.info("\nWatcher stopped.")


def watch_folder_watchdog(conn, watch_folder):
    """Event-based watcher using watchdog library (instant detection)."""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class PDFHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            if event.src_path.lower().endswith(".pdf"):
                # Wait for file to finish writing
                time.sleep(2)
                if os.path.exists(event.src_path):
                    if upload_pdf(conn, event.src_path):
                        move_to_processed(event.src_path, watch_folder)

    observer = Observer()
    observer.schedule(PDFHandler(), watch_folder, recursive=False)
    observer.start()

    log.info(f"Watching folder: {watch_folder}")
    log.info("Using watchdog (instant file detection). Press Ctrl+C to stop.")
    log.info(f"Drop PDF files into this folder to auto-upload to Snowflake.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        log.info("\nWatcher stopped.")
    observer.join()


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="E.D.I.E. PDF Watcher — auto-upload PDFs to Snowflake")
    parser.add_argument("--folder", default=DEFAULT_WATCH_FOLDER, help=f"Folder to watch (default: {DEFAULT_WATCH_FOLDER})")
    parser.add_argument("--once", action="store_true", help="Upload existing files and exit (no watching)")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds (default: 5)")
    args = parser.parse_args()

    watch_folder = os.path.abspath(args.folder)

    # Create folder if it doesn't exist
    os.makedirs(watch_folder, exist_ok=True)
    log.info(f"Watch folder: {watch_folder}")

    # Connect to Snowflake
    conn = get_connection()

    # Process any existing files
    existing = process_existing_files(conn, watch_folder)
    if existing:
        log.info(f"Processed {existing} existing PDF(s).")

    if args.once:
        log.info("Done (--once mode). Exiting.")
        conn.close()
        return

    # Watch for new files
    try:
        watch_folder_watchdog(conn, watch_folder)
    except ImportError:
        log.info("watchdog not installed, using polling mode. Install with: pip install watchdog")
        watch_folder_polling(conn, watch_folder, args.interval)

    conn.close()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════╗
    ║   E.D.I.E. Local PDF Auto-Uploader      ║
    ║   Insurance AI Hub                       ║
    ╚══════════════════════════════════════════╝
    """)
    main()
