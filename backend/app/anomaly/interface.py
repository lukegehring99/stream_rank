"""Interface and data structures for anomaly detection."""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol


@dataclass
class ViewershipData:
    """Container for viewership time series data."""
    
    livestream_id: int
    youtube_video_id: str
    name: str
    channel: str
    timestamps: List[datetime]
    viewcounts: List[int]
    
    @property
    def is_empty(self) -> bool:
        """Check if there's no data."""
        return len(self.viewcounts) == 0
    
    @property
    def latest_viewcount(self) -> Optional[int]:
        """Get the most recent viewcount."""
        if self.is_empty:
            return None
        return self.viewcounts[-1]
    
    @property
    def latest_timestamp(self) -> Optional[datetime]:
        """Get the most recent timestamp."""
        if self.is_empty:
            return None
        return self.timestamps[-1]


@dataclass
class AnomalyScore:
    """Result of anomaly detection for a single stream."""
    
    livestream_id: int
    youtube_video_id: str
    name: str
    channel: str
    score: float  # 0-100 normalized score
    current_viewers: Optional[int]
    last_updated: Optional[datetime]
    
    # Additional debug info
    baseline_mean: Optional[float] = None
    recent_mean: Optional[float] = None
    raw_score: Optional[float] = None


class AnomalyStrategy(Protocol):
    """Protocol for anomaly detection strategies.
    
    Implement this protocol to create new anomaly detection algorithms.
    The strategy should take viewership data and return a normalized score.
    """
    
    def calculate_score(
        self,
        recent_data: List[int],
        baseline_data: List[int],
    ) -> tuple[float, dict]:
        """Calculate anomaly score from viewership data.
        
        Args:
            recent_data: Recent viewership counts (e.g., last 15 minutes)
            baseline_data: Historical baseline counts (e.g., last 24 hours)
            
        Returns:
            Tuple of (normalized_score 0-100, debug_info dict)
        """
        ...
    
    @property
    def name(self) -> str:
        """Strategy name for logging/debugging."""
        ...
