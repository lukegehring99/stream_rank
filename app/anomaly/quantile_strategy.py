"""
Quantile-Based Anomaly Detection Strategy
=========================================

Detects viewership anomalies by comparing percentiles of recent data
against the historical baseline distribution.

Mathematical Approach:
---------------------
The quantile method is robust to outliers and handles skewed distributions
well, which is common in livestream viewership data.

Algorithm:
1. Compute the P-th percentile of baseline data (e.g., 75th percentile)
   - This represents the "expected high" viewership
   
2. Compute the Q-th percentile of recent data (e.g., 90th percentile)  
   - This represents current viewership (robust to momentary spikes)
   
3. Calculate the spike ratio:
   spike_ratio = recent_percentile / baseline_percentile
   
4. If spike_ratio > threshold (e.g., 1.5):
   - Stream is "trending" - viewership is significantly above normal
   
5. Apply logistic normalization to map spike_ratio to 0-100 scale:
   - Uses sigmoid function for smooth S-curve mapping
   - Midpoint at 0 (spike_ratio of 1.0 maps to ~50)
   - Compresses extreme values while maintaining resolution in middle range

Why Quantiles?
--------------
- Robust to outliers: A single massive viewer spike won't skew the baseline
- Distribution-agnostic: Works for normal, log-normal, and multimodal distributions
- Interpretable: "90th percentile is 2x the historical 75th percentile"
- Configurable sensitivity: Adjust percentiles for different use cases

Note: Data validation (insufficient data, inactive streams) is handled by
the AsyncAnomalyDetector orchestration layer, not by individual strategies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import numpy as np

from app.anomaly.config import AnomalyConfig, QuantileParams
from app.anomaly.logistic import logistic_normalize
from app.anomaly.protocol import (
    AnomalyStrategy,
    AnomalyScore,
    AnomalyStatus,
    ViewershipData,
)


@dataclass
class QuantileStrategy:
    """
    Quantile-based anomaly detection for trending livestreams.
    
    Compares the high percentile of recent viewership against
    the historical baseline to detect unusual spikes.
    
    Attributes:
        config: Main anomaly detection configuration
        params: Quantile-specific parameters
    
    Example:
        config = AnomalyConfig(algorithm='quantile')
        strategy = QuantileStrategy(config)
        
        score = strategy.compute_score(recent_data, baseline_data)
        if score.is_trending:
            print(f"Stream {score.livestream_id} is trending!")
    """
    config: AnomalyConfig
    params: Optional[QuantileParams] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = self.config.quantile_params
    
    @property
    def name(self) -> str:
        """Strategy identifier."""
        return "quantile"
    
    def validate_data(
        self,
        recent_data: ViewershipData,
        baseline_data: ViewershipData,
        min_recent: int,
        min_baseline: int,
    ) -> Optional[AnomalyStatus]:
        """
        Validate input data meets minimum requirements.
        
        Returns:
            AnomalyStatus if validation fails, None if valid
        """
        if recent_data.sample_count < min_recent:
            return AnomalyStatus.INSUFFICIENT_DATA
        if baseline_data.sample_count < min_baseline:
            return AnomalyStatus.INSUFFICIENT_DATA
        return None
    
    def compute_score(
        self,
        recent_data: ViewershipData,
        baseline_data: ViewershipData,
    ) -> AnomalyScore:
        """
        Compute quantile-based anomaly score.
        
        The algorithm:
        1. Compute baseline percentile (e.g., 75th) - "normal high"
        2. Compute recent percentile (e.g., 90th) - "current state"  
        3. Calculate spike ratio = recent / baseline
        4. Normalize to 0-100 score
        
        Args:
            recent_data: Recent viewership (last 15-30 min)
            baseline_data: Historical baseline (last 24-48 hrs)
        
        Returns:
            AnomalyScore with normalized score and statistics
        """
        
        # Extract viewcount arrays
        recent_views = recent_data.viewcounts.astype(np.float64)
        baseline_views = baseline_data.viewcounts.astype(np.float64)
        
        # Compute percentiles
        baseline_percentile = np.percentile(
            baseline_views, 
            self.params.baseline_percentile
        )
        recent_percentile = np.percentile(
            recent_views,
            self.params.recent_percentile
        )
        
        # Compute statistics for reporting
        baseline_mean = float(np.mean(baseline_views))
        baseline_std = float(np.std(baseline_views))
        recent_mean = float(np.mean(recent_views))
        
        # Apply floor to baseline to prevent division issues
        # Use max of: explicit floor, 1% of baseline mean, or 1.0
        baseline_floor = max(
            baseline_mean * 0.01,
            1.0
        )
        baseline_percentile = max(baseline_percentile, baseline_floor)
        
        # Calculate spike ratio
        spike_ratio = recent_percentile / baseline_percentile

        normalized_score = logistic_normalize(spike_ratio, self.config)
        
        # Determine status
        status = (
            AnomalyStatus.TRENDING 
            if spike_ratio >= self.params.spike_threshold
            else AnomalyStatus.NORMAL
        )
        
        return AnomalyScore(
            livestream_id=recent_data.livestream_id,
            youtube_video_id=recent_data.youtube_video_id,
            score=normalized_score,
            status=status,
            current_viewcount=recent_data.latest_viewcount,
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
            recent_mean=recent_mean,
            raw_score=spike_ratio,
            algorithm=self.name,
            computed_at=datetime.utcnow(),
            metadata={
                'baseline_percentile': float(baseline_percentile),
                'recent_percentile': float(recent_percentile),
                'spike_ratio': float(spike_ratio),
                #'traffic_boost': float(traffic_boost),
                'baseline_p': self.params.baseline_percentile,
                'recent_p': self.params.recent_percentile,
            }
        )
