"""SQLAlchemy database models for Alma TV."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class Video(Base):
    """Video metadata from the media library."""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    episode_code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    play_history: Mapped[list["PlayHistory"]] = relationship(
        "PlayHistory", back_populates="video"
    )

    def __repr__(self) -> str:
        return f"<Video(series={self.series}, episode={self.episode_code})>"


class SessionStatus(PyEnum):
    """Status of a viewing session."""

    PLANNED = "planned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Session(Base):
    """Planned or completed viewing session."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    show_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), nullable=False, default=SessionStatus.PLANNED
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    intro_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outro_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    play_history: Mapped[list["PlayHistory"]] = relationship(
        "PlayHistory", back_populates="session"
    )

    def __repr__(self) -> str:
        return f"<Session(date={self.show_date}, status={self.status})>"


class PlayHistory(Base):
    """History of played videos."""

    __tablename__ = "play_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id"), nullable=False)
    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id"), nullable=False)
    slot_order: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="play_history")
    video: Mapped["Video"] = relationship("Video", back_populates="play_history")
    feedback: Mapped[Optional["Feedback"]] = relationship(
        "Feedback", back_populates="play_history", uselist=False
    )

    def __repr__(self) -> str:
        return f"<PlayHistory(video_id={self.video_id}, slot={self.slot_order})>"


class Rating(PyEnum):
    """Feedback rating values."""

    LIKED = "liked"
    OKAY = "okay"
    NEVER = "never"


class Feedback(Base):
    """User feedback on played videos."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    play_history_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("play_history.id"), nullable=False, unique=True
    )
    rating: Mapped[Rating] = mapped_column(Enum(Rating), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    play_history: Mapped["PlayHistory"] = relationship("PlayHistory", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<Feedback(rating={self.rating})>"


class Request(Base):
    """Parent/child requests for specific shows."""

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    requester_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    fulfilled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Request(date={self.request_date}, fulfilled={self.fulfilled})>"
