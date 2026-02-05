"""
Z-Score Based Anomaly Detection Strategy
========================================

Detects viewership anomalies by measuring how many standard deviations
the current viewership is from the historical mean.

Mathematical Approach:
---------------------
The Z-score (standard score) measures the distance from the mean in 
units of standard deviation:

    z = (x - μ) / σ

Where:
- x = current observation (recent viewership)
- μ = population mean (baseline mean)
- σ = population standard deviation (baseline std)

A Z-score of 2.0 means the observation is 2 standard deviations above
the mean, which is unusual (occurs ~2.3% of the time in normal distribution).

Modified Z-Score (MAD-based):
-----------------------------
For robustness against outliers, we also support the Modified Z-Score
using Median Absolute Deviation (MAD):

    modified_z = 0.6745 * (x - median) / MAD

Where:
- MAD = median(|xi - median(x)|) for all xi
- 0.6745 is the consistency constant for normal distributions

The MAD-based approach is preferred for livestream data because:
- Viral moments create extreme outliers
- Viewership distributions are often heavily skewed
- MAD is much more robust to outliers than standard deviation

Algorithm Steps:
1. Compute baseline statistics (mean/median, std/MAD)
2. Compute recent representative value (mean or high percentile)
3. Calculate Z-score or Modified Z-score
4. If Z-score > threshold → trending
5. Normalize to 0-100 scale

Edge Cases:
- Zero standard deviation: Apply minimum floor
- Negative Z-scores: Optionally clamp to 0 (we only care about spikes)
- New streams: Return INSUFFICIENT_DATA
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import numpy as np

from app.anomaly.config import AnomalyConfig, ZScoreParams
from app.anomaly.protocol import (
    AnomalyStrategy,
    AnomalyScore,
    AnomalyStatus,
    ViewershipData,
)


# Consistency constant for MAD to approximate standard deviation
# For normal distributions: σ ≈ 1.4826 * MAD
MAD_CONSTANT = 1.4826

# Constant for modified Z-score calculation
MODIFIED_Z_CONSTANT = 0.6745


@dataclass
class ZScoreStrategy:
    """
    Z-score based anomaly detection for trending livestreams.
    
    Measures how many standard deviations current viewership
    deviates from the historical baseline.
    
    Attributes:
        config: Main anomaly detection configuration
        params: Z-score specific parameters
    
    Example:
        config = AnomalyConfig(algorithm='zscore')
        strategy = ZScoreStrategy(config)
        
        score = strategy.compute_score(recent_data, baseline_data)
        print(f"Z-score: {score.raw_score:.2f}")
    """
    config: AnomalyConfig
    params: Optional[ZScoreParams] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = self.config.zscore_params
    
    @property
    def name(self) -> str:
        """Strategy identifier."""
        return "zscore"
    
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
        Compute Z-score based anomaly score.
        
        The algorithm:
        1. Compute baseline central tendency and spread
        2. Compute recent representative value
        3. Calculate (modified) Z-score
        4. Normalize to 0-100 score
        
        Args:
            recent_data: Recent viewership (last 15-30 min)
            baseline_data: Historical baseline (last 24-48 hrs)
        
        Returns:
            AnomalyScore with Z-score and statistics
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
        
        # Check for inactive stream
        if self._is_inactive(recent_data, baseline_data):
            return self._make_error_score(
                recent_data,
                AnomalyStatus.INACTIVE,
                reason="Stream appears inactive",
            )
        
        # Extract viewcount arrays as float for calculations
        recent_views = recent_data.viewcounts.astype(np.float64)
        baseline_views = baseline_data.viewcounts.astype(np.float64)
        
        # Choose calculation method
        if self.params.use_modified_zscore:
            z_score, center, spread = self._compute_modified_zscore(
                recent_views, baseline_views
            )
        else:
            z_score, center, spread = self._compute_standard_zscore(
                recent_views, baseline_views
            )
        
        # Optionally clamp negative Z-scores (below-average viewership)
        if self.params.clamp_negative and z_score < 0:
            z_score = 0.0
        
        # Compute additional statistics
        baseline_mean = float(np.mean(baseline_views))
        baseline_std = float(np.std(baseline_views))
        recent_mean = float(np.mean(recent_views))
        
        # Normalize to 0-100 score
        normalized_score = self._normalize_score(z_score)
        
        # Determine status
        status = (
            AnomalyStatus.TRENDING
            if z_score >= self.params.zscore_threshold
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
            raw_score=z_score,
            algorithm=self.name,
            computed_at=datetime.utcnow(),
            metadata={
                'zscore': float(z_score),
                'center': float(center),
                'spread': float(spread),
                'use_modified': self.params.use_modified_zscore,
                'zscore_threshold': self.params.zscore_threshold,
            }
        )
    
    def _compute_standard_zscore(
        self,
        recent_views: np.ndarray,
        baseline_views: np.ndarray,
    ) -> tuple[float, float, float]:
        """
        Compute standard Z-score using mean and standard deviation.
        
        Formula: z = (x - μ) / σ
        
        Args:
            recent_views: Recent viewership values
            baseline_views: Baseline viewership values
        
        Returns:
            Tuple of (z_score, mean, std_dev)
        """
        # Baseline statistics
        baseline_mean = np.mean(baseline_views)
        baseline_std = np.std(baseline_views)
        
        # Apply minimum floor to standard deviation
        baseline_std = max(baseline_std, self.params.min_std_floor)
        
        # Use 90th percentile of recent data as the "current" value
        # This is more robust than using the latest single value
        recent_value = np.percentile(recent_views, 90)
        
        # Compute Z-score
        z_score = (recent_value - baseline_mean) / baseline_std
        
        return z_score, baseline_mean, baseline_std
    
    def _compute_modified_zscore(
        self,
        recent_views: np.ndarray,
        baseline_views: np.ndarray,
    ) -> tuple[float, float, float]:
        """
        Compute Modified Z-score using Median Absolute Deviation (MAD).
        
        The Modified Z-score is more robust to outliers:
        
        Formula: modified_z = 0.6745 * (x - median) / MAD
        
        Where MAD = median(|xi - median(x)|)
        
        The constant 0.6745 is the 75th percentile of the standard
        normal distribution, making MAD comparable to std dev.
        
        Args:
            recent_views: Recent viewership values
            baseline_views: Baseline viewership values
        
        Returns:
            Tuple of (modified_z_score, median, mad)
        """
        # Baseline statistics using median and MAD
        baseline_median = np.median(baseline_views)
        
        # Compute MAD: median of absolute deviations from median
        absolute_deviations = np.abs(baseline_views - baseline_median)
        mad = np.median(absolute_deviations)
        
        # Apply minimum floor to MAD
        # Convert min_std_floor to equivalent MAD scale
        min_mad = self.params.min_std_floor / MAD_CONSTANT
        mad = max(mad, min_mad)
        
        # Use 90th percentile of recent data
        recent_value = np.percentile(recent_views, 90)
        
        # Compute Modified Z-score
        modified_z = MODIFIED_Z_CONSTANT * (recent_value - baseline_median) / mad
        
        return modified_z, baseline_median, mad
    
    def _is_inactive(
        self,
        recent_data: ViewershipData,
        baseline_data: ViewershipData,
    ) -> bool:
        """
        Check if stream appears inactive.
        
        A stream is considered inactive if:
        - Recent median viewership is 0
        - OR recent max is very low compared to baseline
        """
        if recent_data.is_empty:
            return True
        
        recent_median = np.median(recent_data.viewcounts)
        recent_max = np.max(recent_data.viewcounts)
        
        # Zero viewership
        if recent_median == 0 and recent_max == 0:
            return True
        
        # Dramatic drop from baseline
        if not baseline_data.is_empty:
            baseline_median = np.median(baseline_data.viewcounts)
            if baseline_median > 100 and recent_max < baseline_median * 0.01:
                return True
        
        return False
    
    def _normalize_score(self, z_score: float) -> float:
        """
        Normalize Z-score to 0-100 scale.
        
        Mapping:
        - z ≤ 0 → 0 (at or below mean)
        - z = threshold (2.0) → 50 (just anomalous)  
        - z ≥ 5.0 → 100 (highly anomalous)
        
        Uses sigmoid-like function for smooth distribution.
        """
        if z_score <= 0:
            return self.config.score_min
        
        if z_score >= 5.0:
            return self.config.score_max
        
        # Use sigmoid-like function centered at threshold
        # This gives ~50 at threshold and approaches 100 asymptotically
        threshold = self.params.zscore_threshold
        
        # Scaled logistic function
        # f(z) = 100 / (1 + exp(-k*(z - mid)))
        # where mid is chosen so f(threshold) ≈ 50
        k = 1.0  # Steepness
        mid = threshold  # Center point
        
        # Logistic function scaled to 0-100
        normalized = 100.0 / (1.0 + np.exp(-k * (z_score - mid)))
        
        # Ensure we stay within bounds
        return np.clip(
            normalized,
            self.config.score_min,
            self.config.score_max
        )
    
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
