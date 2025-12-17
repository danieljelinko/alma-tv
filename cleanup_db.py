#!/usr/bin/env python3
"""
Database Cleanup Script.
Removes video entries from the database if the file no longer exists on disk.
"""

from pathlib import Path
from alma_tv.database.session import get_db
from alma_tv.database.models import Video, PlayHistory
from alma_tv.logging.config import configure_logging, get_logger

def main():
    configure_logging(log_level="INFO", enable_console=True)
    logger = get_logger("cleanup")
    
    logger.info("Starting database cleanup...")
    
    removed_count = 0
    
    with get_db() as db:
        videos = db.query(Video).all()
        logger.info(f"Checking {len(videos)} videos...")
        
        for video in videos:
            file_path = Path(video.path)
            if not file_path.exists():
                logger.info(f"Removing missing file: {video.path}")
                
                # Delete associated PlayHistory records first
                db.query(PlayHistory).filter(PlayHistory.video_id == video.id).delete()
                
                db.delete(video)
                removed_count += 1
        
        if removed_count > 0:
            db.commit()
            logger.info(f"Successfully removed {removed_count} missing videos.")
        else:
            logger.info("No missing videos found.")

if __name__ == "__main__":
    main()
