"""Quantile-based anomaly detection strategy."""
import statistics
from typing import List

from .config import QuantileParams


class QuantileStrategy:
    """Quantile-based anomaly detection.
    
    Compares the recent viewership percentile against the historical baseline.
    A high score indicates the recent viewership is unusually high compared
    to the historical pattern.
    
    Algorithm:
    1. Calculate the baseline percentile (e.g., 75th percentile of last 24h)
    2. Calculate the recent percentile (e.g., median of last 15min)
    3. Score = how far recent is above baseline, normalized to 0-100
    """
    
    def __init__(self, params: QuantileParams = None):
        self.params = params or QuantileParams()
    
    @property
    def name(self) -> str:
        return "quantile"
    
    def calculate_score(
        self,
        recent_data: List[int],
        baseline_data: List[int],
    ) -> tuple[float, dict]:
        """Calculate anomaly score using quantile comparison.
        
        Returns:
            Tuple of (normalized_score 0-100, debug_info)
        """
        debug_info = {
            "recent_count": len(recent_data),
            "baseline_count": len(baseline_data),
        }
        
        # Need minimum data for baseline
        if len(baseline_data) < self.params.min_baseline_points:
            debug_info["reason"] = "insufficient_baseline_data"
            return 0.0, debug_info
        
        # Need at least one recent point
        if len(recent_data) == 0:
            debug_info["reason"] = "no_recent_data"
            return 0.0, debug_info
        
        # Calculate baseline percentile
        sorted_baseline = sorted(baseline_data)
        baseline_idx = int(len(sorted_baseline) * self.params.baseline_percentile / 100)
        baseline_idx = min(baseline_idx, len(sorted_baseline) - 1)
        baseline_value = sorted_baseline[baseline_idx]
        
        # Calculate recent percentile (median by default)
        sorted_recent = sorted(recent_data)
        recent_idx = int(len(sorted_recent) * self.params.recent_percentile / 100)
        recent_idx = min(recent_idx, len(sorted_recent) - 1)
        recent_value = sorted_recent[recent_idx]
        
        debug_info["baseline_value"] = baseline_value
        debug_info["recent_value"] = recent_value
        
        # Avoid division by zero
        if baseline_value == 0:
            if recent_value > 0:
                # Any viewers when baseline is 0 is significant
                score = 100.0
            else:
                score = 0.0
            debug_info["reason"] = "zero_baseline"
            return score, debug_info
        
        # Calculate ratio and normalize to 0-100
        ratio = recent_value / baseline_value
        debug_info["ratio"] = ratio
        
        # Normalize: ratio of 1.0 = 50, ratio of 2.0 = 100, ratio of 0.5 = 0
        # Using sigmoid-like normalization
        if ratio <= 0.5:
            score = 0.0
        elif ratio >= 2.0:
            score = 100.0
        else:
            # Linear interpolation between 0.5 and 2.0
            score = (ratio - 0.5) / 1.5 * 100
        
        debug_info["raw_score"] = ratio
        return round(score, 2), debug_info
