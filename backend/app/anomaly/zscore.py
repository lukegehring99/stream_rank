"""Z-score based anomaly detection strategy."""
import statistics
from typing import List

from .config import ZScoreParams


class ZScoreStrategy:
    """Z-score based anomaly detection.
    
    Measures how many standard deviations the recent viewership is
    from the historical mean. Optionally uses Median Absolute Deviation
    (MAD) for robustness to outliers.
    
    Algorithm:
    1. Calculate mean and std of baseline data
    2. Calculate mean of recent data
    3. Z-score = (recent_mean - baseline_mean) / baseline_std
    4. Normalize to 0-100 scale
    """
    
    def __init__(self, params: ZScoreParams = None):
        self.params = params or ZScoreParams()
    
    @property
    def name(self) -> str:
        return "zscore"
    
    def calculate_score(
        self,
        recent_data: List[int],
        baseline_data: List[int],
    ) -> tuple[float, dict]:
        """Calculate anomaly score using z-score.
        
        Returns:
            Tuple of (normalized_score 0-100, debug_info)
        """
        debug_info = {
            "recent_count": len(recent_data),
            "baseline_count": len(baseline_data),
            "use_mad": self.params.use_mad,
        }
        
        # Need minimum data for baseline
        if len(baseline_data) < self.params.min_baseline_points:
            debug_info["reason"] = "insufficient_baseline_data"
            return 0.0, debug_info
        
        # Need at least one recent point
        if len(recent_data) == 0:
            debug_info["reason"] = "no_recent_data"
            return 0.0, debug_info
        
        # Calculate baseline statistics
        if self.params.use_mad:
            baseline_center, baseline_spread = self._calculate_mad_stats(baseline_data)
            debug_info["method"] = "MAD"
        else:
            baseline_center = statistics.mean(baseline_data)
            baseline_spread = statistics.stdev(baseline_data) if len(baseline_data) > 1 else 0
            debug_info["method"] = "stddev"
        
        # Calculate recent mean
        recent_mean = statistics.mean(recent_data)
        
        debug_info["baseline_mean"] = baseline_center
        debug_info["baseline_spread"] = baseline_spread
        debug_info["recent_mean"] = recent_mean
        
        # Handle zero variance
        if baseline_spread == 0:
            if recent_mean > baseline_center:
                score = 100.0
            elif recent_mean < baseline_center:
                score = 0.0
            else:
                score = 50.0
            debug_info["reason"] = "zero_variance"
            return score, debug_info
        
        # Calculate z-score
        zscore = (recent_mean - baseline_center) / baseline_spread
        debug_info["zscore"] = zscore
        
        # Cap z-score for normalization
        capped_zscore = max(-self.params.max_zscore, min(self.params.max_zscore, zscore))
        
        # Normalize to 0-100 (z=0 -> 50, z=max -> 100, z=-max -> 0)
        score = 50 + (capped_zscore / self.params.max_zscore) * 50
        
        debug_info["raw_score"] = zscore
        return round(score, 2), debug_info
    
    def _calculate_mad_stats(self, data: List[int]) -> tuple[float, float]:
        """Calculate Median Absolute Deviation statistics.
        
        MAD is more robust to outliers than standard deviation.
        
        Returns:
            Tuple of (median, mad_scaled)
        """
        median = statistics.median(data)
        deviations = [abs(x - median) for x in data]
        mad = statistics.median(deviations)
        
        # Scale MAD to be comparable to standard deviation
        # For normal distribution: std ≈ 1.4826 * MAD
        mad_scaled = mad * 1.4826
        
        return median, mad_scaled
