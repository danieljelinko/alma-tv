"""Lineup generator for daily viewing sessions."""

import random
from datetime import date, datetime, timedelta
from typing import List, Optional

from alma_tv.config import get_settings
from alma_tv.database import PlayHistory, Session, Video, get_db
from alma_tv.database.models import SessionStatus
from alma_tv.library.service import LibraryService
from alma_tv.logging.config import get_logger
from alma_tv.scheduler.weights import WeightCalculator

logger = get_logger(__name__)


class LineupGenerator:
    """
    Generate daily viewing lineups.

    Ensures:
    - Runtime target (default 30 minutes ± 1 minute)
    - 3-5 episodes
    - Series and season diversity
    - Anti-repeat window (default 14 days)
    - Respects feedback weights
    - Handles explicit requests
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize lineup generator.

        Args:
            seed: Random seed for deterministic testing
        """
        self.settings = get_settings()
        self.library = LibraryService()
        self.weights = WeightCalculator()

        if seed is not None:
            random.seed(seed)

    def generate_lineup(
        self,
        target_date: date,
        target_duration_minutes: Optional[int] = None,
        min_episodes: int = 3,
        max_episodes: int = 5,
        request_payload: Optional[dict] = None,
    ) -> Optional[int]:
        """
        Generate lineup for a specific date.

        Args:
            target_date: Date for the lineup
            target_duration_minutes: Target duration (defaults to config)
            min_episodes: Minimum number of episodes
            max_episodes: Maximum number of episodes
            request_payload: Optional request dict (e.g., {"requests": [{"series": "Bluey", "count": 3}]})
                             Legacy format {"series": "Bluey"} is also supported.

        Returns:
            Session ID if successful, None otherwise
        """
        if target_duration_minutes is None:
            target_duration_minutes = self.settings.target_duration_minutes

        target_duration_seconds = target_duration_minutes * 60

        # Reserve time for intro/outro
        intro_duration = self._get_file_duration(self.settings.intro_path) if self.settings.intro_path.exists() else 0
        outro_duration = self._get_file_duration(self.settings.outro_path) if self.settings.outro_path.exists() else 0

        available_duration = target_duration_seconds - intro_duration - outro_duration

        logger.info(
            f"Generating lineup for {target_date}: target {target_duration_minutes}m, "
            f"available {available_duration}s after intro/outro"
        )

        # Check if lineup already exists
        with get_db() as db:
            existing = (
                db.query(Session)
                .filter(Session.show_date == datetime.combine(target_date, datetime.min.time()))
                .first()
            )
            if existing:
                logger.warning(f"Lineup already exists for {target_date}: session {existing.id}")
                return existing.id

        # Parse requests
        requests = []
        if request_payload:
            if "requests" in request_payload:
                requests = request_payload["requests"]
            elif "series" in request_payload:
                # Legacy support
                count = request_payload.get("count", 3) # Default legacy count? Or implied?
                # The old logic filtered exclusively. Let's assume legacy means "only this series".
                # But here we want to support "include X".
                # Let's treat legacy as "include X" but maybe with high count?
                # Actually, let's just map it.
                requests = [{"series": request_payload["series"], "count": request_payload.get("count", 3)}]

        # Build candidate pool
        candidates = self._build_candidate_pool(
            cooldown_days=self.settings.repeat_cooldown_days,
            requests=requests,
        )

        if not candidates:
            logger.error("No candidate episodes available")
            return None

        # Calculate weights
        video_ids = [v.id for v in candidates]
        weights = self.weights.calculate_weights_batch(video_ids)

        # Apply request multiplier
        for req in requests:
            requested_series = req["series"]
            for video in candidates:
                if video.series == requested_series:
                    weights[video.id] *= 3.0

        # Select episodes
        selected = self._select_episodes(
            candidates=candidates,
            weights=weights,
            available_duration=available_duration,
            min_episodes=min_episodes,
            max_episodes=max_episodes,
            requests=requests,
        )

        if not selected:
            logger.error("Could not select episodes for lineup")
            return None

        # Create session
        session_id = self._create_session(
            target_date=target_date,
            selected_videos=selected,
            intro_path=self.settings.intro_path,
            outro_path=self.settings.outro_path,
        )

        # Log KPIs
        self._log_kpis(selected, weights)

        return session_id

    def _build_candidate_pool(
        self,
        cooldown_days: int,
        requests: List[dict] = None,
        request_payload: Optional[dict] = None, # Kept for compatibility if called internally
    ) -> List[Video]:
        """
        Build pool of candidate episodes.

        Args:
            cooldown_days: Cooldown period in days
            requests: List of request dicts
            request_payload: Legacy payload (deprecated)

        Returns:
            List of candidate videos
        """
        # Start with all enabled videos
        candidates = self.library.list_episodes(disabled=False)

        # Legacy support
        if request_payload and "series" in request_payload and not requests:
            requested_series = request_payload["series"]
            # Legacy behavior: STRICT filtering
            candidates = [v for v in candidates if v.series == requested_series]
            return candidates

        # Exclude recently played
        with get_db() as db:
            cooldown_date = datetime.utcnow() - timedelta(days=cooldown_days)
            recent_plays = (
                db.query(PlayHistory.video_id)
                .filter(PlayHistory.started_at >= cooldown_date)
                .filter(PlayHistory.completed == True)
                .all()
            )
            recent_ids = {row.video_id for row in recent_plays}

        # If we have requests, we MUST include episodes from requested series even if recently played?
        # Or should we respect cooldown?
        # Usually explicit request overrides cooldown.
        
        requested_series_names = {r["series"] for r in requests} if requests else set()
        
        filtered_candidates = []
        for v in candidates:
            # If video is in requested series, include it (ignore cooldown)
            if v.series in requested_series_names:
                filtered_candidates.append(v)
            # Otherwise, respect cooldown
            elif v.id not in recent_ids:
                filtered_candidates.append(v)

        logger.info(f"Candidate pool: {len(filtered_candidates)} episodes")
        return filtered_candidates

    def _select_episodes(
        self,
        candidates: List[Video],
        weights: dict[int, float],
        available_duration: int,
        min_episodes: int,
        max_episodes: int,
        requests: List[dict] = None,
    ) -> List[Video]:
        """
        Select episodes using weighted random selection.

        Args:
            candidates: Candidate videos
            weights: Weight dict
            available_duration: Available duration in seconds
            min_episodes: Minimum episodes to select
            max_episodes: Maximum episodes to select
            requests: List of requests to fulfill

        Returns:
            List of selected videos
        """
        selected = []
        total_duration = 0
        used_series_seasons = set()
        
        # Filter out zero-weight candidates
        valid_candidates = [v for v in candidates if weights.get(v.id, 0) > 0]

        # 1. Fulfill requests first
        if requests:
            for req in requests:
                series = req["series"]
                count = req["count"]
                
                # Get candidates for this series
                series_candidates = [v for v in valid_candidates if v.series == series]
                
                # Select 'count' episodes
                # Use weighted selection among them
                for _ in range(count):
                    if not series_candidates:
                        logger.warning(f"Not enough episodes to fulfill request for {series}")
                        break
                        
                    weight_list = [weights[v.id] for v in series_candidates]
                    if sum(weight_list) == 0:
                        break
                        
                    chosen = random.choices(series_candidates, weights=weight_list, k=1)[0]
                    
                    # Add to selection
                    selected.append(chosen)
                    total_duration += chosen.duration_seconds
                    used_series_seasons.add((chosen.series, chosen.season))
                    
                    # Remove from pools
                    valid_candidates.remove(chosen)
                    series_candidates.remove(chosen)
                    
                    logger.info(f"Selected requested: {chosen.series} {chosen.episode_code}")

        # 2. Fill remaining slots
        while len(selected) < max_episodes:
            # Check duration limit (soft limit, can go over slightly if under min episodes? No, strict on max duration usually)
            # But we have a tolerance.
            
            # Try to maintain diversity
            diverse_candidates = [
                v
                for v in valid_candidates
                if (v.series, v.season) not in used_series_seasons
            ]

            # If we need more episodes and diversity pool is empty, use all candidates
            if not diverse_candidates and len(selected) < min_episodes:
                diverse_candidates = valid_candidates

            if not diverse_candidates:
                break

            # Weighted random selection
            population = diverse_candidates
            weight_list = [weights[v.id] for v in population]

            if sum(weight_list) == 0:
                break

            chosen = random.choices(population, weights=weight_list, k=1)[0]

            # Check if adding this episode keeps us within duration target
            new_total = total_duration + chosen.duration_seconds

            # Allow some flexibility (±60s)
            if new_total <= available_duration + 60:
                selected.append(chosen)
                total_duration = new_total
                used_series_seasons.add((chosen.series, chosen.season))
                valid_candidates.remove(chosen)

                logger.debug(
                    f"Selected: {chosen.series} {chosen.episode_code} "
                    f"({chosen.duration_seconds}s, weight: {weights[chosen.id]:.2f})"
                )
            else:
                # If we can't fit this one, maybe try another? 
                # For simplicity, we just skip it and remove from pool to try others?
                # Or just break if we are close enough?
                valid_candidates.remove(chosen) # Try to find a shorter one?
                continue

            # Stop if we're close to target and have minimum episodes
            if len(selected) >= min_episodes and abs(new_total - available_duration) < 60:
                break

        logger.info(
            f"Selected {len(selected)} episodes, total duration: {total_duration}s "
            f"(target: {available_duration}s, variance: {total_duration - available_duration}s)"
        )

        return selected

    def _create_session(
        self,
        target_date: date,
        selected_videos: List[Video],
        intro_path: Optional[str],
        outro_path: Optional[str],
    ) -> int:
        """
        Create session and play history entries.

        Args:
            target_date: Date for session
            selected_videos: Selected videos
            intro_path: Path to intro video
            outro_path: Path to outro video

        Returns:
            Session ID
        """
        total_duration = sum(v.duration_seconds for v in selected_videos)

        with get_db() as db:
            # Create session
            session = Session(
                show_date=datetime.combine(target_date, datetime.min.time()),
                status=SessionStatus.PLANNED,
                intro_path=str(intro_path) if intro_path else None,
                outro_path=str(outro_path) if outro_path else None,
                total_duration_seconds=total_duration,
            )
            db.add(session)
            db.flush()

            # Create play history entries
            for slot_order, video in enumerate(selected_videos, start=1):
                play_history = PlayHistory(
                    session_id=session.id,
                    video_id=video.id,
                    slot_order=slot_order,
                    completed=False,
                )
                db.add(play_history)

            logger.info(f"Created session {session.id} for {target_date} with {len(selected_videos)} episodes")
            return session.id

    def _get_file_duration(self, file_path) -> int:
        """
        Get duration of a file.

        Args:
            file_path: Path to file

        Returns:
            Duration in seconds (0 if file doesn't exist)
        """
        from pathlib import Path
        from alma_tv.library.scanner import Scanner

        if not Path(file_path).exists():
            return 0

        scanner = Scanner()
        duration = scanner.get_duration(Path(file_path))
        return duration or 0

    def _log_kpis(self, selected: List[Video], weights: dict[int, float]) -> None:
        """
        Log KPI metrics for monitoring.

        Args:
            selected: Selected videos
            weights: Weight dict
        """
        if not selected:
            return

        selected_weights = [weights[v.id] for v in selected]
        durations = [v.duration_seconds for v in selected]

        import statistics

        variance = statistics.stdev(durations) if len(durations) > 1 else 0.0

        logger.info(
            f"KPIs - Weight: mean={statistics.mean(selected_weights):.3f}, "
            f"Duration: mean={statistics.mean(durations):.1f}s, "
            f"variance={variance:.1f}s"
        )
