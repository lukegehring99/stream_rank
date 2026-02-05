"""
Anomaly Detection Protocol (Interface)
======================================

Defines the Strategy pattern interface for anomaly detection algorithms.
All detection strategies must implement the AnomalyStrategy protocol.

Mathematical Background:
------------------------
Anomaly detection in time-series viewership data aims to identify streams
that are experiencing unusual viewer engagement compared to their baseline.

Key Concepts:
- Recent Window: A short sliding window (e.g., 15-30 min) representing "now"
- Baseline Window: A longer historical window (e.g., 24-48 hrs) representing "normal"
- Anomaly Score: Normalized measure (0-100) of how unusual current viewership is

The higher the score, the more "trending" the stream is considered.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol, List, Optional, runtime_checkable
import numpy as np
from numpy.typing import NDArray


class AnomalyStatus(str, Enum):
    """Status codes for anomaly detection results."""
    NORMAL = "normal"              # Stream is within expected range
    TRENDING = "trending"          # Stream is experiencing a viewership spike
    INSUFFICIENT_DATA = "insufficient_data"  # Not enough data points
    INACTIVE = "inactive"          # Stream appears to be offline/inactive
    ERROR = "error"                # Detection failed


@dataclass
class ViewershipData:
    """
    Container for viewership time-series data.
    
    Attributes:
        livestream_id: Database ID of the livestream
        youtube_video_id: YouTube's video ID
        timestamps: Array of measurement timestamps (UTC)
        viewcounts: Array of viewer counts at each timestamp
    """
    livestream_id: int
    youtube_video_id: str
    timestamps: NDArray[np.datetime64]
    viewcounts: NDArray[np.int64]
    
    def __post_init__(self):
        if len(self.timestamps) != len(self.viewcounts):
            raise ValueError("timestamps and viewcounts must have same length")
    
    @property
    def is_empty(self) -> bool:
        """Check if there's no data."""
        return len(self.viewcounts) == 0
    
    @property
    def sample_count(self) -> int:
        """Number of data points."""
        return len(self.viewcounts)
    
    @property
    def latest_timestamp(self) -> Optional[datetime]:
        """Most recent timestamp, or None if empty."""
        if self.is_empty:
            return None
        return self.timestamps[-1].astype('datetime64[us]').astype(datetime)
    
    @property
    def latest_viewcount(self) -> Optional[int]:
        """Most recent viewcount, or None if empty."""
        if self.is_empty:
            return None
        return int(self.viewcounts[-1])
    
    def slice_recent(self, cutoff: np.datetime64) -> "ViewershipData":
        """Get data after the cutoff time (recent window)."""
        mask = self.timestamps >= cutoff
        return ViewershipData(
            livestream_id=self.livestream_id,
            youtube_video_id=self.youtube_video_id,
            timestamps=self.timestamps[mask],
            viewcounts=self.viewcounts[mask],
        )
    
    def slice_baseline(self, start: np.datetime64, end: np.datetime64) -> "ViewershipData":
        """Get data within a time range (baseline window)."""
        mask = (self.timestamps >= start) & (self.timestamps < end)
        return ViewershipData(
            livestream_id=self.livestream_id,
            youtube_video_id=self.youtube_video_id,
            timestamps=self.timestamps[mask],
            viewcounts=self.viewcounts[mask],
        )


@dataclass
class AnomalyScore:
    """
    Result of anomaly detection for a single livestream.
    
    Attributes:
        livestream_id: Database ID of the livestream
        youtube_video_id: YouTube's video ID  
        score: Normalized anomaly score (0-100, higher = more anomalous)
        status: Status code indicating detection result
        current_viewcount: Most recent viewer count
        baseline_mean: Mean viewership in baseline window
        baseline_std: Standard deviation in baseline window
        recent_mean: Mean viewership in recent window
        raw_score: Un-normalized score from the algorithm
        algorithm: Name of the algorithm used
        computed_at: Timestamp when score was computed
        metadata: Additional algorithm-specific data
    """
    livestream_id: int
    youtube_video_id: str
    score: float
    status: AnomalyStatus
    current_viewcount: Optional[int] = None
    baseline_mean: Optional[float] = None
    baseline_std: Optional[float] = None
    recent_mean: Optional[float] = None
    raw_score: Optional[float] = None
    algorithm: str = ""
    computed_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'livestream_id': self.livestream_id,
            'youtube_video_id': self.youtube_video_id,
            'score': round(self.score, 2),
            'status': self.status.value,
            'current_viewcount': self.current_viewcount,
            'baseline_mean': round(self.baseline_mean, 2) if self.baseline_mean else None,
            'baseline_std': round(self.baseline_std, 2) if self.baseline_std else None,
            'recent_mean': round(self.recent_mean, 2) if self.recent_mean else None,
            'raw_score': round(self.raw_score, 4) if self.raw_score else None,
            'algorithm': self.algorithm,
            'computed_at': self.computed_at.isoformat(),
        }
    
    @property
    def is_trending(self) -> bool:
        """Check if stream is classified as trending."""
        return self.status == AnomalyStatus.TRENDING
    
    @property
    def is_valid(self) -> bool:
        """Check if detection produced a valid result."""
        return self.status in (AnomalyStatus.NORMAL, AnomalyStatus.TRENDING)


@runtime_checkable
class AnomalyStrategy(Protocol):
    """
    Protocol (interface) for anomaly detection strategies.
    
    All anomaly detection algorithms must implement this interface,
    enabling the Strategy pattern for swappable algorithms.
    
    The Strategy Pattern:
    --------------------
    This pattern allows algorithms to be selected at runtime without
    changing the code that uses them. Each strategy encapsulates a
    specific detection algorithm.
    
    Implementing a New Strategy:
    ---------------------------
    1. Create a class that implements compute_score() and name property
    2. The compute_score method receives recent and baseline ViewershipData
    3. Return an AnomalyScore with normalized score (0-100)
    
    Example:
        class MyCustomStrategy:
            @property
            def name(self) -> str:
                return "my_custom_strategy"
            
            def compute_score(
                self,
                recent_data: ViewershipData,
                baseline_data: ViewershipData,
            ) -> AnomalyScore:
                # Your custom algorithm here
                ...
    """
    
    @property
    def name(self) -> str:
        """
        Unique identifier for this strategy.
        
        Returns:
            Strategy name (e.g., 'quantile', 'zscore', 'moving_average')
        """
        ...
    
    def compute_score(
        self,
        recent_data: ViewershipData,
        baseline_data: ViewershipData,
    ) -> AnomalyScore:
        """
        Compute anomaly score for a livestream.
        
        This is the core method that each strategy must implement.
        It receives time-series data for the recent window and 
        historical baseline, and returns a normalized anomaly score.
        
        Args:
            recent_data: Viewership data from the recent window 
                (e.g., last 15-30 minutes)
            baseline_data: Viewership data from the historical baseline
                (e.g., last 24-48 hours, excluding recent window)
        
        Returns:
            AnomalyScore with:
            - score: Normalized value between 0-100
            - status: Detection status (NORMAL, TRENDING, etc.)
            - Supporting statistics (means, std devs, etc.)
        
        Raises:
            ValueError: If data is invalid or incompatible
        """
        ...
    
    def validate_data(
        self,
        recent_data: ViewershipData,
        baseline_data: ViewershipData,
        min_recent: int,
        min_baseline: int,
    ) -> Optional[AnomalyStatus]:
        """
        Validate input data meets minimum requirements.
        
        Default implementation checks sample counts. Strategies can
        override for additional validation.
        
        Args:
            recent_data: Recent viewership data
            baseline_data: Baseline viewership data
            min_recent: Minimum required recent samples
            min_baseline: Minimum required baseline samples
        
        Returns:
            AnomalyStatus if validation fails, None if data is valid
        """
        ...
