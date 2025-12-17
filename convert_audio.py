#!/usr/bin/env python3
"""
Audio Converter for Alma TV.
Converts audio tracks of video files to AAC (stereo) for browser compatibility.
"""

import subprocess
import sys
from pathlib import Path
import shutil

def convert_video(input_path: Path):
    """Convert video audio to AAC."""
    output_path = input_path.with_suffix('.converted.mp4')
    
    print(f"Converting: {input_path}")
    print(f"Output: {output_path}")
    
    # ffmpeg command:
    # -i input
    # -c:v copy (copy video stream without re-encoding)
    # -c:a aac (convert audio to AAC)
    # -b:a 192k (audio bitrate)
    # -ac 2 (force stereo, important for browser compatibility)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",
        str(output_path)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("Conversion successful!")
        
        # Backup original
        backup_path = input_path.with_suffix(input_path.suffix + ".bak")
        shutil.move(input_path, backup_path)
        print(f"Original backed up to: {backup_path}")
        
        # Move converted to original name (but keep mp4 extension if it changed)
        # Actually, let's keep the new extension if it changed, but we need to update the DB?
        # The scanner will pick it up as a new file if extension changes.
        # If we rename .mkv to .mp4, scanner sees new file.
        # If we keep .mkv, browser might complain? Chrome plays .mkv if codecs are right.
        # But .mp4 is safer.
        
        # Let's replace the original file with the converted one, but ensure extension is .mp4
        final_path = input_path.with_suffix('.mp4')
        shutil.move(output_path, final_path)
        print(f"Replaced with converted file: {final_path}")
        
        if final_path != input_path:
            print(f"Note: File extension changed from {input_path.suffix} to .mp4")
            # We might need to delete the old file entry from DB or let scanner handle it.
            # Scanner will see old file gone and new file added.
            
    except subprocess.CalledProcessError as e:
        print(f"Error converting {input_path}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_audio.py <directory_or_file>")
        sys.exit(1)
        
    target = Path(sys.argv[1])
    
    if target.is_file():
        convert_video(target)
    elif target.is_dir():
        # Find all video files
        extensions = {'.mp4', '.mkv', '.avi'}
        for ext in extensions:
            for file_path in target.rglob(f"*{ext}"):
                if "converted" in file_path.name or file_path.suffix == ".bak":
                    continue
                # Check if it needs conversion? 
                # For now, just convert everything in the target dir if user asks.
                # Or maybe just Bluey?
                if "Bluey" in str(file_path):
                     convert_video(file_path)
    else:
        print("Invalid path")

if __name__ == "__main__":
    main()
