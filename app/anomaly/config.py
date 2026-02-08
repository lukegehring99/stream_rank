"""
Anomaly Detection Configuration
===============================

Dataclasses for configuring anomaly detection algorithms.
All time windows and thresholds are centralized here for easy tuning.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class AlgorithmType(str, Enum):
    """Supported anomaly detection algorithms."""
    QUANTILE = "quantile"
    ZSCORE = "zscore"


@dataclass(frozen=True)
class QuantileParams:
    """
    Parameters for quantile-based anomaly detection.
    
    The algorithm compares the recent viewership percentile against 
    the historical baseline to detect unusual spikes.
    
    Attributes:
        baseline_percentile: The percentile of historical data to use as baseline.
            Default 75 means we compare against the 75th percentile of historical views.
        recent_percentile: The percentile of recent data to represent current state.
            Default 90 means we use the 90th percentile of recent views (robust to outliers).
        spike_threshold: Minimum ratio of recent/baseline to be considered anomalous.
            Default 1.5 means viewership must be 50% higher than baseline.
        high_traffic_multiplier: Extra weight for streams with very high absolute viewership.
            Helps prioritize truly popular streams even with moderate relative growth.
    """
    baseline_percentile: float = 75.0
    recent_percentile: float = 90.0
    spike_threshold: float = 1.5
    high_traffic_multiplier: float = 1.2
    
    def __post_init__(self):
        if not 0 <= self.baseline_percentile <= 100:
            raise ValueError("baseline_percentile must be between 0 and 100")
        if not 0 <= self.recent_percentile <= 100:
            raise ValueError("recent_percentile must be between 0 and 100")
        if self.spike_threshold < 1.0:
            raise ValueError("spike_threshold must be >= 1.0")


@dataclass(frozen=True)
class ZScoreParams:
    """
    Parameters for Z-score based anomaly detection.
    
    The algorithm measures how many standard deviations the current 
    viewership is above/below the historical mean.
    
    Attributes:
        zscore_threshold: Minimum Z-score to be considered anomalous.
            Default 2.0 means viewership must be 2 standard deviations above mean.
        use_modified_zscore: If True, use Median Absolute Deviation (MAD) for 
            robustness against outliers. Recommended for livestream data.
        min_std_floor: Minimum standard deviation to prevent division issues
            when viewership is very stable.
        clamp_negative: If True, clamp negative Z-scores to 0 (we only care about spikes).
    """
    zscore_threshold: float = 2.0
    use_modified_zscore: bool = True
    min_std_floor: float = 10.0  # Minimum std dev to avoid div-by-zero issues
    clamp_negative: bool = True
    
    def __post_init__(self):
        if self.zscore_threshold < 0:
            raise ValueError("zscore_threshold must be >= 0")
        if self.min_std_floor <= 0:
            raise ValueError("min_std_floor must be > 0")


@dataclass
class AnomalyConfig:
    """
    Main configuration for the anomaly detection system.
    
    Attributes:
        recent_window_minutes: Size of the recent window in minutes (default: 15).
            This captures the "current" state of viewership.
        baseline_hours: Size of the historical baseline in hours (default: 24).
            This establishes what "normal" viewership looks like.
        min_recent_samples: Minimum data points needed in recent window.
            Streams with fewer samples are marked as INSUFFICIENT_DATA.
        min_baseline_samples: Minimum data points needed in baseline.
            New streams may not have enough history for reliable detection.
        algorithm: Which algorithm to use ('quantile' or 'zscore').
        quantile_params: Parameters for quantile-based algorithm.
        zscore_params: Parameters for Z-score based algorithm.
        score_min: Minimum normalized score (default: 0).
        score_max: Maximum normalized score (default: 100).
        inactive_threshold_minutes: A stream with no data in this many minutes
            is considered inactive (default: 60).
    
    Example:
        # Conservative config for catching only major spikes
        config = AnomalyConfig(
            recent_window_minutes=30,
            baseline_hours=48,
            algorithm='quantile',
            quantile_params=QuantileParams(spike_threshold=2.0),
        )
        
        # Aggressive config for catching smaller trends
        config = AnomalyConfig(
            recent_window_minutes=10,
            baseline_hours=12,
            algorithm='zscore',
            zscore_params=ZScoreParams(zscore_threshold=1.5),
        )
    """
    # Time windows
    recent_window_minutes: int = 15
    baseline_hours: int = 24
    
    # Minimum sample requirements
    min_recent_samples: int = 5
    min_baseline_samples: int = 1000
    
    # Algorithm selection
    algorithm: Literal["quantile", "zscore"] = "quantile"
    
    # Algorithm-specific parameters
    quantile_params: QuantileParams = field(default_factory=QuantileParams)
    zscore_params: ZScoreParams = field(default_factory=ZScoreParams)
    
    # Score normalization
    score_min: float = 0.0
    score_max: float = 100.0
    
    # Inactive stream handling
    inactive_threshold_minutes: int = 60

    # Logistic normalization parameters
    logistic_midpoint: float = 0.0
    logistic_steepness: float = 1.0
    
    def __post_init__(self):
        if self.recent_window_minutes < 5:
            raise ValueError("recent_window_minutes must be >= 5")
        if self.baseline_hours < 1:
            raise ValueError("baseline_hours must be >= 1")
        if self.min_recent_samples < 1:
            raise ValueError("min_recent_samples must be >= 1")
        if self.min_baseline_samples < 2:
            raise ValueError("min_baseline_samples must be >= 2")
        if self.score_min >= self.score_max:
            raise ValueError("score_min must be < score_max")
    
    @property
    def recent_window_seconds(self) -> int:
        """Recent window in seconds."""
        return self.recent_window_minutes * 60
    
    @property
    def baseline_seconds(self) -> int:
        """Baseline window in seconds."""
        return self.baseline_hours * 3600
    
    def get_algorithm_type(self) -> AlgorithmType:
        """Get the algorithm type enum."""
        return AlgorithmType(self.algorithm)
