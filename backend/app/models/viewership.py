"""Viewership history model."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .livestream import Livestream


class ViewershipHistory(Base):
    """Time series viewership data for a livestream."""
    
    __tablename__ = "viewership_history"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    livestream_id: Mapped[int] = mapped_column(
        ForeignKey("livestreams.id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    viewcount: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Relationships
    livestream: Mapped["Livestream"] = relationship(
        "Livestream",
        back_populates="viewership_history",
    )
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_viewership_timestamp", "timestamp"),
        Index("idx_viewership_livestream_timestamp", "livestream_id", "timestamp"),
        Index("idx_viewership_anomaly_detection", "livestream_id", "timestamp", "viewcount"),
    )
    
    def __repr__(self) -> str:
        return f"<ViewershipHistory(id={self.id}, livestream_id={self.livestream_id}, viewcount={self.viewcount})>"
