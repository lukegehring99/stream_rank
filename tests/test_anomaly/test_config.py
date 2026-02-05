"""
Tests for anomaly detection configuration.
"""

import pytest
from app.anomaly.config import (
    AnomalyConfig,
    QuantileParams,
    ZScoreParams,
    AlgorithmType,
)


class TestQuantileParams:
    """Tests for QuantileParams dataclass."""
    
    def test_default_values(self):
        """Test default parameter values."""
        params = QuantileParams()
        
        assert params.baseline_percentile == 75.0
        assert params.recent_percentile == 90.0
        assert params.spike_threshold == 1.5
        assert params.high_traffic_multiplier == 1.2
    
    def test_custom_values(self):
        """Test custom parameter values."""
        params = QuantileParams(
            baseline_percentile=50.0,
            recent_percentile=95.0,
            spike_threshold=2.0,
        )
        
        assert params.baseline_percentile == 50.0
        assert params.recent_percentile == 95.0
        assert params.spike_threshold == 2.0
    
    def test_invalid_percentile_low(self):
        """Test validation for percentile < 0."""
        with pytest.raises(ValueError, match="baseline_percentile"):
            QuantileParams(baseline_percentile=-1.0)
    
    def test_invalid_percentile_high(self):
        """Test validation for percentile > 100."""
        with pytest.raises(ValueError, match="recent_percentile"):
            QuantileParams(recent_percentile=101.0)
    
    def test_invalid_threshold(self):
        """Test validation for spike_threshold < 1."""
        with pytest.raises(ValueError, match="spike_threshold"):
            QuantileParams(spike_threshold=0.5)


class TestZScoreParams:
    """Tests for ZScoreParams dataclass."""
    
    def test_default_values(self):
        """Test default parameter values."""
        params = ZScoreParams()
        
        assert params.zscore_threshold == 2.0
        assert params.use_modified_zscore is True
        assert params.min_std_floor == 10.0
        assert params.clamp_negative is True
    
    def test_custom_values(self):
        """Test custom parameter values."""
        params = ZScoreParams(
            zscore_threshold=3.0,
            use_modified_zscore=False,
            min_std_floor=5.0,
        )
        
        assert params.zscore_threshold == 3.0
        assert params.use_modified_zscore is False
        assert params.min_std_floor == 5.0
    
    def test_invalid_threshold(self):
        """Test validation for negative threshold."""
        with pytest.raises(ValueError, match="zscore_threshold"):
            ZScoreParams(zscore_threshold=-1.0)
    
    def test_invalid_std_floor(self):
        """Test validation for non-positive std floor."""
        with pytest.raises(ValueError, match="min_std_floor"):
            ZScoreParams(min_std_floor=0.0)


class TestAnomalyConfig:
    """Tests for main AnomalyConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = AnomalyConfig()
        
        assert config.recent_window_minutes == 15
        assert config.baseline_hours == 24
        assert config.min_recent_samples == 3
        assert config.min_baseline_samples == 10
        assert config.algorithm == "quantile"
        assert config.score_min == 0.0
        assert config.score_max == 100.0
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = AnomalyConfig(
            recent_window_minutes=30,
            baseline_hours=48,
            algorithm='zscore',
        )
        
        assert config.recent_window_minutes == 30
        assert config.baseline_hours == 48
        assert config.algorithm == 'zscore'
    
    def test_time_conversions(self):
        """Test time conversion properties."""
        config = AnomalyConfig(
            recent_window_minutes=15,
            baseline_hours=24,
        )
        
        assert config.recent_window_seconds == 15 * 60
        assert config.baseline_seconds == 24 * 3600
    
    def test_algorithm_type_property(self):
        """Test algorithm type enum conversion."""
        config = AnomalyConfig(algorithm='quantile')
        assert config.get_algorithm_type() == AlgorithmType.QUANTILE
        
        config = AnomalyConfig(algorithm='zscore')
        assert config.get_algorithm_type() == AlgorithmType.ZSCORE
    
    def test_invalid_recent_window(self):
        """Test validation for too small recent window."""
        with pytest.raises(ValueError, match="recent_window_minutes"):
            AnomalyConfig(recent_window_minutes=2)
    
    def test_invalid_baseline_hours(self):
        """Test validation for too small baseline."""
        with pytest.raises(ValueError, match="baseline_hours"):
            AnomalyConfig(baseline_hours=0)
    
    def test_invalid_score_range(self):
        """Test validation for invalid score range."""
        with pytest.raises(ValueError, match="score_min"):
            AnomalyConfig(score_min=100, score_max=50)
    
    def test_nested_params(self):
        """Test nested parameter configuration."""
        config = AnomalyConfig(
            quantile_params=QuantileParams(spike_threshold=2.0),
            zscore_params=ZScoreParams(zscore_threshold=3.0),
        )
        
        assert config.quantile_params.spike_threshold == 2.0
        assert config.zscore_params.zscore_threshold == 3.0
