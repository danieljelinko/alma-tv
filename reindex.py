#!/usr/bin/env python3
"""
Reindex Library Script.
Scans the media directory and updates the database.
"""

from alma_tv.library.scanner import Scanner
from alma_tv.config import get_settings
from alma_tv.logging.config import configure_logging

def main():
    configure_logging(log_level="INFO", enable_console=True)
    
    settings = get_settings()
    print(f"Scanning library at: {settings.media_root}")
    
    scanner = Scanner(settings.media_root)
    stats = scanner.scan_directory()
    
    print("\nScan Complete!")
    print(f"Scanned: {stats.get('scanned', 0)}")
    print(f"Added:   {stats.get('added', 0)}")
    print(f"Updated: {stats.get('updated', 0)}")
    print(f"Failed:  {stats.get('failed', 0)}")

if __name__ == "__main__":
    main()
