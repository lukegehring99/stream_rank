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
   
5. Normalize to 0-100 score:
   - Score = 0 when spike_ratio ≤ 1.0 (at or below baseline)
   - Score = 100 when spike_ratio = 3.0 (3x baseline, configurable)
   - Linear interpolation between

Why Quantiles?
--------------
- Robust to outliers: A single massive viewer spike won't skew the baseline
- Distribution-agnostic: Works for normal, log-normal, and multimodal distributions
- Interpretable: "90th percentile is 2x the historical 75th percentile"
- Configurable sensitivity: Adjust percentiles for different use cases

Edge Cases Handled:
- New streams: Return INSUFFICIENT_DATA if baseline too short
- Inactive streams: Detected via zero/near-zero viewership
- Zero baseline: Floor applied to prevent division by zero
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import numpy as np

from app.anomaly.config import AnomalyConfig, QuantileParams
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
        # Validate data sufficiency
        validation_status = self.validate_data(
            recent_data,
            baseline_data,
            self.config.min_recent_samples,
            self.config.min_baseline_samples,
        )
        
        if validation_status is not None:
            return self._make_error_score(
                recent_data,
                validation_status,
                reason="Insufficient data points",
            )
        
        # Check for inactive stream (all zeros or very low counts)
        if self._is_inactive(recent_data, baseline_data):
            return self._make_error_score(
                recent_data,
                AnomalyStatus.INACTIVE,
                reason="Stream appears inactive",
            )
        
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
        
        # Apply high-traffic multiplier for popular streams
        # Streams with many viewers get a slight boost
        traffic_boost = self._compute_traffic_boost(recent_mean)
        adjusted_ratio = spike_ratio * traffic_boost
        
        # Normalize to 0-100 score
        # - ratio ≤ 1.0 → score = 0 (at or below baseline)
        # - ratio = threshold → score = 50 (just became anomalous)
        # - ratio = 3.0 → score = 100 (significantly elevated)
        normalized_score = self._normalize_score(adjusted_ratio)
        
        # Determine status
        status = (
            AnomalyStatus.TRENDING 
            if adjusted_ratio >= self.params.spike_threshold
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
            raw_score=adjusted_ratio,
            algorithm=self.name,
            computed_at=datetime.utcnow(),
            metadata={
                'baseline_percentile': float(baseline_percentile),
                'recent_percentile': float(recent_percentile),
                'spike_ratio': float(spike_ratio),
                'traffic_boost': float(traffic_boost),
                'baseline_p': self.params.baseline_percentile,
                'recent_p': self.params.recent_percentile,
            }
        )
    
    def _is_inactive(
        self, 
        recent_data: ViewershipData, 
        baseline_data: ViewershipData
    ) -> bool:
        """
        Check if stream appears inactive.
        
        A stream is considered inactive if:
        - Recent median viewership is 0
        - OR recent max is very low compared to baseline median
        """
        if recent_data.is_empty:
            return True
            
        recent_median = np.median(recent_data.viewcounts)
        recent_max = np.max(recent_data.viewcounts)
        
        # Check for zero viewership
        if recent_median == 0 and recent_max == 0:
            return True
        
        # Check for dramatic drop from baseline
        if not baseline_data.is_empty:
            baseline_median = np.median(baseline_data.viewcounts)
            if baseline_median > 100 and recent_max < baseline_median * 0.01:
                return True
        
        return False
    
    def _compute_traffic_boost(self, recent_mean: float) -> float:
        """
        Compute traffic-based score boost.
        
        High-traffic streams get a slight multiplier to help them
        rank higher when they have comparable relative growth.
        
        The boost is logarithmic to prevent massive streams from
        completely dominating.
        
        Args:
            recent_mean: Mean recent viewership
        
        Returns:
            Multiplier between 1.0 and high_traffic_multiplier
        """
        if recent_mean <= 100:
            return 1.0
        
        # Logarithmic boost: log10(viewers/100) scaled
        # 100 viewers → 1.0
        # 1000 viewers → ~1.1
        # 10000 viewers → ~1.2
        log_boost = np.log10(recent_mean / 100) * 0.1
        
        max_boost = self.params.high_traffic_multiplier - 1.0
        return 1.0 + min(log_boost, max_boost)
    
    def _normalize_score(self, ratio: float) -> float:
        """
        Normalize spike ratio to 0-100 scale.
        
        Mapping:
        - ratio ≤ 1.0 → 0 (at or below baseline)
        - ratio = 1.5 (threshold) → 50 (just anomalous)
        - ratio ≥ 3.0 → 100 (very anomalous)
        
        Uses smooth sigmoid-like curve for natural ranking.
        """
        if ratio <= 1.0:
            return self.config.score_min
        
        if ratio >= 3.0:
            return self.config.score_max
        
        # Linear interpolation from 1.0→3.0 to 0→100
        # Centered at threshold (~50 when ratio = 1.5)
        normalized = (ratio - 1.0) / (3.0 - 1.0)
        
        # Apply slight curve to spread out middle values
        # This uses a power function for smoother distribution
        curved = np.power(normalized, 0.8)
        
        score_range = self.config.score_max - self.config.score_min
        return self.config.score_min + (curved * score_range)
    
    def _make_error_score(
        self,
        data: ViewershipData,
        status: AnomalyStatus,
        reason: str,
    ) -> AnomalyScore:
        """Create an AnomalyScore for error/edge cases."""
        return AnomalyScore(
            livestream_id=data.livestream_id,
            youtube_video_id=data.youtube_video_id,
            score=0.0,
            status=status,
            current_viewcount=data.latest_viewcount,
            algorithm=self.name,
            computed_at=datetime.utcnow(),
            metadata={'reason': reason}
        )
