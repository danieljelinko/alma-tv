"""Database session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from alma_tv.config import get_settings
from alma_tv.database.models import Base

_engine = None
_SessionLocal = None


def init_db() -> None:
    """Initialize database engine and create tables."""
    global _engine, _SessionLocal

    settings = get_settings()
    print(f"DEBUG: Initializing DB with URL: {settings.database_url}")
    
    _engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    )

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

    # Create all tables
    Base.metadata.create_all(bind=_engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.

    Usage:
        with get_db() as db:
            db.query(Video).all()
    """
    if _SessionLocal is None:
        init_db()

    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
