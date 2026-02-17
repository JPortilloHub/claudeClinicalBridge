"""Database connection and session management.

Uses lazy initialization to avoid failing when PostgreSQL isn't available
(e.g., during testing or when only running the CLI).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.python.utils.config import settings

# Build PostgreSQL connection URL
SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)

# Base class for models (safe to create without a connection)
Base = declarative_base()

# Lazily initialized engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the SQLAlchemy engine (lazy)."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_session_factory():
    """Get or create the session factory (lazy)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


# Convenience alias for background tasks
def SessionLocal():
    """Create a new database session."""
    factory = get_session_factory()
    return factory()


def get_db():
    """Dependency for FastAPI routes to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_tables():
    """Create all database tables. Call on app startup."""
    Base.metadata.create_all(bind=get_engine())
