import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alma_tv.config.settings import Settings
from alma_tv.database.models import Base
import alma_tv.database.session

@pytest.fixture(scope="session")
def test_settings(tmp_path_factory):
    """Override settings for tests."""
    media_root = tmp_path_factory.mktemp("media")
    settings = Settings(
        database_url="sqlite:///:memory:",
        media_root=media_root,
        intro_path=media_root / "intro.mp4",
        outro_path=media_root / "outro.mp4",
        log_file=tmp_path_factory.mktemp("logs") / "test.log",
        clock_svg_path=tmp_path_factory.mktemp("cache") / "clock.svg",
    )
    
    # Create dummy files
    settings.intro_path.touch()
    settings.outro_path.touch()
    
    return settings

@pytest.fixture(scope="session", autouse=True)
def mock_settings(test_settings):
    """Patch get_settings to return test settings."""
    with patch("alma_tv.config.get_settings", return_value=test_settings):
        yield

@pytest.fixture(scope="function")
def db_session(test_settings):
    """Create a clean database session for each test."""
    # Use StaticPool to share in-memory DB across threads/connections
    engine = create_engine(
        test_settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    # Patch globals in alma_tv.database.session so get_db() uses our engine/session
    # We patch _SessionLocal to be our factory (TestingSessionLocal)
    # We patch init_db to do nothing
    
    # Prevent get_db from closing the session
    real_close = session.close
    session.close = MagicMock()
    
    with patch("alma_tv.database.session._engine", engine), \
         patch("alma_tv.database.session._SessionLocal", lambda: session), \
         patch("alma_tv.database.session.init_db"):
        
        yield session
    
    # Restore and close
    real_close()
    Base.metadata.drop_all(engine)
