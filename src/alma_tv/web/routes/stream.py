"""Video streaming support for Alma TV."""

import os
from pathlib import Path
from typing import Generator

from starlette.responses import StreamingResponse
from starlette.requests import Request


def get_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    """Parse Range header."""
    if not range_header:
        return 0, file_size - 1
    
    try:
        unit, ranges = range_header.split("=")
        if unit != "bytes":
            return 0, file_size - 1
        
        start_str, end_str = ranges.split("-")
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
        
        return start, end
    except ValueError:
        return 0, file_size - 1


def file_iterator(path: Path, start: int, end: int, chunk_size: int = 8192) -> Generator[bytes, None, None]:
    """Yield file chunks."""
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def stream_video(request: Request, video_path: Path) -> StreamingResponse:
    """
    Stream video file with Range support.
    
    Args:
        request: The Starlette/FastAPI request object
        video_path: Path to the video file
        
    Returns:
        StreamingResponse with appropriate headers
    """
    if not video_path.exists():
        return StreamingResponse(iter([]), status_code=404)

    file_size = video_path.stat().st_size
    range_header = request.headers.get("range")
    
    start, end = get_range_header(range_header, file_size)
    
    # Ensure valid range
    if start >= file_size or end >= file_size:
        return StreamingResponse(iter([]), status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    chunk_size = end - start + 1
    
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "video/mp4",  # Assuming MP4 for now
    }
    
    return StreamingResponse(
        file_iterator(video_path, start, end),
        status_code=206,
        headers=headers
    )
