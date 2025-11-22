"""Request parser for natural language inputs."""

import re
from difflib import get_close_matches
from typing import Any, Dict, List, Optional

from alma_tv.config import get_settings
from alma_tv.database import Video, get_db
from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


class RequestParser:
    """Parse natural language requests into structured data."""

    def __init__(self):
        """Initialize parser."""
        self.settings = get_settings()
        self.number_map = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }

    def parse(self, text: str) -> tuple[int, List[Dict[str, Any]]]:
        """
        Parse text into date offset and list of request objects.

        Example:
            "tomorrow one blueie" ->
            (1, [{"series": "Bluey", "count": 1}])

        Args:
            text: Input text

        Returns:
            Tuple of (days_offset, list of request dicts)
            days_offset: 0 for today, 1 for tomorrow
        """
        text = text.lower()
        requests = []
        days_offset = 0

        # Extract date keywords
        if "tomorrow" in text:
            days_offset = 1
            text = text.replace("tomorrow", "")
        if "today" in text:
            days_offset = 0
            text = text.replace("today", "")

        # Split by "and" or "," to handle multiple requests
        parts = re.split(r" and |,", text)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            count = 1
            series_keyword = part

            # Extract count
            words = part.split()
            if words and words[0] in self.number_map:
                count = self.number_map[words[0]]
                series_keyword = " ".join(words[1:])
            elif words and words[0].isdigit():
                count = int(words[0])
                series_keyword = " ".join(words[1:])

            # Resolve series
            series_name = self._resolve_series(series_keyword)
            if series_name:
                requests.append({"series": series_name, "count": count})
            else:
                logger.warning(f"Could not resolve series for keyword: {series_keyword}")

        return days_offset, requests

    def _resolve_series(self, keyword: str) -> Optional[str]:
        """Resolve keyword to series name."""
        keyword = keyword.strip()
        
        # 1. Check config map
        if keyword in self.settings.keyword_map:
            return self.settings.keyword_map[keyword]

        # 2. Check exact match (case insensitive) against DB
        with get_db() as db:
            # Get all unique series names
            all_series = [
                r[0] for r in db.query(Video.series).distinct().all()
            ]

        for series in all_series:
            if series.lower() == keyword:
                return series

        # 3. Fuzzy match
        matches = get_close_matches(keyword, [s.lower() for s in all_series], n=1, cutoff=0.6)
        if matches:
            # Find original case
            for series in all_series:
                if series.lower() == matches[0]:
                    return series

        return None
