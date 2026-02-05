"""Livestream model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .viewership import ViewershipHistory


class Livestream(Base, TimestampMixin):
    """YouTube livestream metadata."""
    
    __tablename__ = "livestreams"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, 
        default=lambda: str(uuid.uuid4()),
        comment='Public UUID for external references'
    )
    youtube_video_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    is_live: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    
    # Relationships
    viewership_history: Mapped[List["ViewershipHistory"]] = relationship(
        "ViewershipHistory",
        back_populates="livestream",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    
    def __repr__(self) -> str:
        return f"<Livestream(id={self.id}, name='{self.name}', is_live={self.is_live})>"
    
    @classmethod
    def from_youtube_url(cls, url: str, name: str, channel: str, description: str = None) -> "Livestream":
        """Create a Livestream from a YouTube URL."""
        video_id = cls.extract_video_id(url)
        return cls(
            youtube_video_id=video_id,
            name=name,
            channel=channel,
            description=description,
            url=url,
            is_live=True,
        )
    
    @staticmethod
    def extract_video_id(url: str) -> str:
        """Extract video ID from various YouTube URL formats."""
        import re
        
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
            r'^([a-zA-Z0-9_-]{11})$',  # Direct video ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from URL: {url}")
