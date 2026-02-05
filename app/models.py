"""
Trending YouTube Livestreams - SQLAlchemy Models
================================================

Production-ready SQLAlchemy model definitions for the stream_rank application.
Compatible with SQLAlchemy 2.0+ and Flask-SQLAlchemy.

Usage:
    from app.models import db, Livestream, ViewershipHistory, User
    
    # Flask initialization
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://user:pass@localhost/stream_rank'
    db.init_app(app)
"""

from datetime import datetime, timedelta
from typing import Optional, List
import uuid

from sqlalchemy import (
    create_engine, 
    String, 
    Text, 
    Boolean, 
    Integer,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    Session,
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Livestream(Base):
    """
    YouTube livestream metadata.
    
    Stores information about tracked livestreams including their
    current status, channel info, and timestamps.
    """
    __tablename__ = 'livestreams'
    __table_args__ = (
        Index('idx_livestreams_is_live', 'is_live'),
        Index('idx_livestreams_channel', 'channel'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'comment': 'YouTube livestream metadata',
        }
    )

    # Primary key
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    
    # Public UUID (exposed to API to hide internal counts)
    public_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        comment='Public UUID for external references',
    )
    
    # YouTube video ID (always 11 characters)
    youtube_video_id: Mapped[str] = mapped_column(
        String(11),
        unique=True,
        nullable=False,
        comment='YouTube video ID (always 11 chars)',
    )
    
    # Stream metadata
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment='Livestream title',
    )
    
    channel: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment='Channel name',
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment='Stream description',
    )
    
    url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment='Full YouTube URL',
    )
    
    # Status
    is_live: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment='Currently streaming',
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationships
    viewership_history: Mapped[List["ViewershipHistory"]] = relationship(
        "ViewershipHistory",
        back_populates="livestream",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Livestream(id={self.id}, name='{self.name[:30]}...', is_live={self.is_live})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            'id': self.public_id,  # Use public_id for external API
            'youtube_video_id': self.youtube_video_id,
            'name': self.name,
            'channel': self.channel,
            'description': self.description,
            'url': self.url,
            'is_live': self.is_live,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def get_live_streams(cls, session: Session) -> List["Livestream"]:
        """Get all currently live streams."""
        stmt = select(cls).where(cls.is_live == True).order_by(cls.name)
        return list(session.scalars(stmt))
    
    @classmethod
    def get_by_youtube_id(cls, session: Session, youtube_id: str) -> Optional["Livestream"]:
        """Find a livestream by its YouTube video ID."""
        stmt = select(cls).where(cls.youtube_video_id == youtube_id)
        return session.scalar(stmt)


class ViewershipHistory(Base):
    """
    Time-series viewership data.
    
    Stores historical viewer counts at regular intervals for
    trend analysis and anomaly detection.
    """
    __tablename__ = 'viewership_history'
    __table_args__ = (
        # Index for time-range queries
        Index('idx_viewership_timestamp', 'timestamp'),
        # Composite index for per-stream time-series queries
        Index('idx_viewership_livestream_timestamp', 'livestream_id', 'timestamp'),
        # Composite index for anomaly detection queries
        Index('idx_viewership_anomaly_detection', 'livestream_id', 'timestamp', 'viewcount'),
        # Composite index for trending/ranking queries
        Index('idx_viewership_trending', 'timestamp', 'livestream_id', 'viewcount'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'comment': 'Time-series viewership data',
        }
    )

    # Primary key
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    
    # Foreign key to livestreams
    livestream_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey('livestreams.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False,
    )
    
    # Timestamp (UTC)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment='UTC timestamp of measurement',
    )
    
    # Viewer count
    viewcount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment='Concurrent viewer count',
    )
    
    # Relationships
    livestream: Mapped["Livestream"] = relationship(
        "Livestream",
        back_populates="viewership_history",
    )

    def __repr__(self) -> str:
        return f"<ViewershipHistory(id={self.id}, livestream_id={self.livestream_id}, viewcount={self.viewcount})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'livestream_id': self.livestream_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'viewcount': self.viewcount,
        }
    
    @classmethod
    def get_history(
        cls, 
        session: Session, 
        livestream_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> List["ViewershipHistory"]:
        """Get viewership history for a stream within a time range."""
        stmt = (
            select(cls)
            .where(cls.livestream_id == livestream_id)
            .where(cls.timestamp >= start_time)
            .where(cls.timestamp <= end_time)
            .order_by(cls.timestamp)
        )
        return list(session.scalars(stmt))
    
    @classmethod
    def get_latest(cls, session: Session, livestream_id: int) -> Optional["ViewershipHistory"]:
        """Get the most recent viewership record for a stream."""
        stmt = (
            select(cls)
            .where(cls.livestream_id == livestream_id)
            .order_by(cls.timestamp.desc())
            .limit(1)
        )
        return session.scalar(stmt)
    
    @classmethod
    def cleanup_old_data(cls, session: Session, retention_days: int = 30) -> int:
        """
        Delete viewership records older than retention period.
        
        Args:
            session: SQLAlchemy session
            retention_days: Number of days to retain (default: 30)
            
        Returns:
            Number of deleted records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # For large deletions, consider chunking in production
        result = session.execute(
            cls.__table__.delete().where(cls.timestamp < cutoff_date)
        )
        session.commit()
        
        return result.rowcount


class User(Base):
    """
    Admin user account for authentication.
    
    Stores user credentials with bcrypt-hashed passwords.
    """
    __tablename__ = 'users'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_unicode_ci',
        'comment': 'Admin user accounts',
    }

    # Primary key
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    
    # Username
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    
    # Password hash (bcrypt)
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment='bcrypt hash',
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary (excludes password_hash)."""
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def set_password(self, password: str) -> None:
        """Hash and set the user's password using bcrypt."""
        import bcrypt
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        import bcrypt
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )
    
    @classmethod
    def get_by_username(cls, session: Session, username: str) -> Optional["User"]:
        """Find a user by username."""
        stmt = select(cls).where(cls.username == username)
        return session.scalar(stmt)


# ============================================================================
# Database Initialization Helper
# ============================================================================

def init_db(database_url: str, echo: bool = False) -> Session:
    """
    Initialize the database and return a session.
    
    Args:
        database_url: SQLAlchemy database URL
        echo: Whether to echo SQL statements (for debugging)
        
    Returns:
        SQLAlchemy Session instance
        
    Example:
        session = init_db('mysql+pymysql://user:pass@localhost/stream_rank')
    """
    engine = create_engine(database_url, echo=echo)
    Base.metadata.create_all(engine)
    return Session(engine)


# ============================================================================
# Flask-SQLAlchemy Integration (optional)
# ============================================================================

try:
    from flask_sqlalchemy import SQLAlchemy
    
    # Create Flask-SQLAlchemy instance with our Base
    db = SQLAlchemy(model_class=Base)
    
except ImportError:
    # Flask-SQLAlchemy not installed, provide a stub
    db = None
