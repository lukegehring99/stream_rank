"""Configuration for anomaly detection algorithms."""
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class QuantileParams:
    """Parameters for quantile-based anomaly detection."""
    
    # Percentile to use for comparison (0-100)
    baseline_percentile: float = 75.0
    
    # Minimum data points required for baseline
    min_baseline_points: int = 10
    
    # Percentile to compare recent data against
    recent_percentile: float = 50.0


@dataclass
class ZScoreParams:
    """Parameters for z-score based anomaly detection."""
    
    # Use Median Absolute Deviation instead of standard deviation
    # (more robust to outliers)
    use_mad: bool = False
    
    # Minimum data points required for baseline
    min_baseline_points: int = 10
    
    # Maximum z-score for normalization (scores above this are capped)
    max_zscore: float = 10.0


@dataclass
class AnomalyConfig:
    """Configuration for anomaly detection."""
    
    # Algorithm to use
    algorithm: Literal["quantile", "zscore"] = "quantile"
    
    # Time window for recent data (minutes)
    recent_window_minutes: int = 15
    
    # Time window for baseline data (hours)
    baseline_hours: int = 24
    
    # Algorithm-specific parameters
    quantile_params: QuantileParams = field(default_factory=QuantileParams)
    zscore_params: ZScoreParams = field(default_factory=ZScoreParams)
    
    # Default score for streams with insufficient data
    default_score: float = 0.0
    
    # Minimum score to be considered "trending"
    trending_threshold: float = 50.0
