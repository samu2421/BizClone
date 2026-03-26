"""
Database session management.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Create database engine with connection pooling
engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    poolclass=QueuePool,
)


# Event listener to log connection pool status
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when a new connection is created."""
    logger.debug("Database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool."""
    logger.debug("Connection checked out from pool")


# Create session factory
# expire_on_commit=False ensures objects remain usable after commit (e.g. in Celery tasks)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Yields:
        Session: SQLAlchemy database session
        
    Example:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_db_async() -> Generator[Session, None, None]:
    """
    Async dependency function to get database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database.
    Creates all tables if they don't exist.
    
    Note: In production, use Alembic migrations instead.
    """
    from app.db.base import Base
    from app.models import Customer, Call, Transcript, CallEvent, Record  # noqa
    
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def check_db_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def close_db_connection() -> None:
    """Close all database connections."""
    logger.info("Closing database connections...")
    engine.dispose()
    logger.info("Database connections closed")

