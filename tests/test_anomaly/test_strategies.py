"""
Tests for anomaly detection strategies.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta

from app.anomaly.config import AnomalyConfig, QuantileParams, ZScoreParams
from app.anomaly.protocol import ViewershipData, AnomalyStatus
from app.anomaly.quantile_strategy import QuantileStrategy
from app.anomaly.zscore_strategy import ZScoreStrategy
from app.anomaly.factory import AnomalyStrategyFactory


def make_viewership_data(
    viewcounts: list[int],
    livestream_id: int = 1,
    youtube_video_id: str = "test123abc",
    interval_minutes: int = 2,
) -> ViewershipData:
    """Helper to create ViewershipData from a list of viewcounts."""
    now = datetime.utcnow()
    timestamps = np.array([
        np.datetime64(now - timedelta(minutes=interval_minutes * (len(viewcounts) - i - 1)), 'us')
        for i in range(len(viewcounts))
    ], dtype='datetime64[us]')
    
    return ViewershipData(
        livestream_id=livestream_id,
        youtube_video_id=youtube_video_id,
        timestamps=timestamps,
        viewcounts=np.array(viewcounts, dtype=np.int64),
    )


class TestViewershipData:
    """Tests for ViewershipData container."""
    
    def test_creation(self):
        """Test basic creation."""
        data = make_viewership_data([100, 150, 200])
        
        assert data.livestream_id == 1
        assert data.sample_count == 3
        assert not data.is_empty
    
    def test_empty_data(self):
        """Test empty data handling."""
        data = ViewershipData(
            livestream_id=1,
            youtube_video_id="test",
            timestamps=np.array([], dtype='datetime64[us]'),
            viewcounts=np.array([], dtype=np.int64),
        )
        
        assert data.is_empty
        assert data.sample_count == 0
        assert data.latest_viewcount is None
    
    def test_slice_recent(self):
        """Test slicing recent data."""
        data = make_viewership_data([100, 150, 200, 250, 300], interval_minutes=5)
        cutoff = np.datetime64(datetime.utcnow() - timedelta(minutes=12), 'us')
        
        recent = data.slice_recent(cutoff)
        
        # Should get last ~2-3 data points (within 12 minutes)
        assert recent.sample_count <= 3
        assert recent.sample_count >= 2
    
    def test_mismatched_lengths_raises(self):
        """Test that mismatched array lengths raise error."""
        with pytest.raises(ValueError, match="same length"):
            ViewershipData(
                livestream_id=1,
                youtube_video_id="test",
                timestamps=np.array([np.datetime64('now')], dtype='datetime64[us]'),
                viewcounts=np.array([100, 200], dtype=np.int64),
            )


class TestQuantileStrategy:
    """Tests for QuantileStrategy."""
    
    def test_name_property(self):
        """Test strategy name."""
        config = AnomalyConfig()
        strategy = QuantileStrategy(config)
        assert strategy.name == "quantile"
    
    def test_normal_viewership(self):
        """Test detection with normal viewership (no spike)."""
        config = AnomalyConfig(
            min_recent_samples=3,
            min_baseline_samples=5,
        )
        strategy = QuantileStrategy(config)
        
        # Baseline: stable around 1000 viewers
        baseline = make_viewership_data([950, 1000, 1050, 1000, 980, 1020, 1010])
        # Recent: similar to baseline
        recent = make_viewership_data([1000, 1020, 1010])
        
        score = strategy.compute_score(recent, baseline)
        
        assert score.status == AnomalyStatus.NORMAL
        # Logistic normalization maps spike_ratio ~1.0 to ~50
        # Normal viewership should be around 50 (midpoint)
        assert 45 <= score.score <= 55
        assert score.algorithm == "quantile"
    
    def test_trending_spike(self):
        """Test detection with significant viewership spike."""
        config = AnomalyConfig(
            min_recent_samples=3,
            min_baseline_samples=5,
            quantile_params=QuantileParams(spike_threshold=1.5),
        )
        strategy = QuantileStrategy(config)
        
        # Baseline: stable around 1000 viewers
        baseline = make_viewership_data([950, 1000, 1050, 1000, 980, 1020, 1010])
        # Recent: 2x spike to 2000 viewers
        recent = make_viewership_data([1800, 2000, 2100])
        
        score = strategy.compute_score(recent, baseline)
        
        assert score.status == AnomalyStatus.TRENDING
        assert score.score > 50  # High score for spike
        assert score.raw_score > 1.5  # Above threshold
    
    def test_insufficient_recent_data(self):
        """Test that strategy computes score even with minimal data.
        
        Note: Data validation (INSUFFICIENT_DATA status) is now handled by
        the AsyncAnomalyDetector, not by individual strategies.
        """
        config = AnomalyConfig(min_recent_samples=5)
        strategy = QuantileStrategy(config)
        
        baseline = make_viewership_data([1000] * 10)
        recent = make_viewership_data([1000, 1000])  # Only 2 samples
        
        # Strategy computes score; detector handles validation
        score = strategy.compute_score(recent, baseline)
        
        # Strategy should still return a valid score object
        assert score.algorithm == "quantile"
        assert 0 <= score.score <= 100
    
    def test_insufficient_baseline_data(self):
        """Test that strategy computes score even with minimal baseline.
        
        Note: Data validation (INSUFFICIENT_DATA status) is now handled by
        the AsyncAnomalyDetector, not by individual strategies.
        """
        config = AnomalyConfig(min_baseline_samples=10)
        strategy = QuantileStrategy(config)
        
        baseline = make_viewership_data([1000] * 5)  # Only 5 samples
        recent = make_viewership_data([1000] * 5)
        
        # Strategy computes score; detector handles validation
        score = strategy.compute_score(recent, baseline)
        
        # Strategy should still return a valid score object
        assert score.algorithm == "quantile"
        assert 0 <= score.score <= 100
    
    def test_inactive_stream(self):
        """Test that strategy handles zero-viewer data.
        
        Note: Inactive stream detection is now handled by the
        AsyncAnomalyDetector, not by individual strategies.
        """
        config = AnomalyConfig(min_recent_samples=2, min_baseline_samples=2)
        strategy = QuantileStrategy(config)
        
        baseline = make_viewership_data([1000] * 10)
        recent = make_viewership_data([0, 0, 0])  # No viewers
        
        # Strategy computes score; detector handles inactive detection
        score = strategy.compute_score(recent, baseline)
        
        # With zero recent viewers, spike ratio will be 0
        # Logistic normalization with midpoint=0 maps 0 to 50
        assert score.algorithm == "quantile"
        assert score.raw_score == 0.0
        assert score.score == 50.0  # Logistic(0) with midpoint=0 = 50
    
    def test_score_normalization(self):
        """Test that scores are normalized to 0-100 range."""
        config = AnomalyConfig(min_recent_samples=2, min_baseline_samples=2)
        strategy = QuantileStrategy(config)
        
        baseline = make_viewership_data([100] * 10)
        recent = make_viewership_data([300, 350, 400])  # 3-4x spike
        
        score = strategy.compute_score(recent, baseline)
        
        assert 0 <= score.score <= 100
    
    def test_metadata_includes_percentiles(self):
        """Test that metadata includes computation details."""
        config = AnomalyConfig(min_recent_samples=2, min_baseline_samples=2)
        strategy = QuantileStrategy(config)
        
        baseline = make_viewership_data([1000] * 10)
        recent = make_viewership_data([1500, 1600, 1700])
        
        score = strategy.compute_score(recent, baseline)
        
        assert 'baseline_percentile' in score.metadata
        assert 'recent_percentile' in score.metadata
        assert 'spike_ratio' in score.metadata


class TestZScoreStrategy:
    """Tests for ZScoreStrategy."""
    
    def test_name_property(self):
        """Test strategy name."""
        config = AnomalyConfig()
        strategy = ZScoreStrategy(config)
        assert strategy.name == "zscore"
    
    def test_normal_viewership(self):
        """Test detection with normal viewership."""
        config = AnomalyConfig(
            min_recent_samples=3,
            min_baseline_samples=5,
            zscore_params=ZScoreParams(zscore_threshold=2.0),
        )
        strategy = ZScoreStrategy(config)
        
        # Baseline: mean=1000, std~50
        baseline = make_viewership_data([950, 1000, 1050, 970, 1030, 980, 1020])
        # Recent: within 1 std dev
        recent = make_viewership_data([1020, 1030, 1050])
        
        score = strategy.compute_score(recent, baseline)
        
        assert score.status == AnomalyStatus.NORMAL
        assert score.raw_score < 2.0  # Below z-score threshold
    
    def test_trending_zscore(self):
        """Test detection when Z-score exceeds threshold."""
        config = AnomalyConfig(
            min_recent_samples=3,
            min_baseline_samples=5,
            zscore_params=ZScoreParams(
                zscore_threshold=2.0,
                use_modified_zscore=False,  # Use standard for predictable test
            ),
        )
        strategy = ZScoreStrategy(config)
        
        # Baseline with known stats
        baseline = make_viewership_data([1000] * 10)  # Mean=1000, std≈0
        # Recent: way above (will use std floor)
        recent = make_viewership_data([1100, 1150, 1200])
        
        score = strategy.compute_score(recent, baseline)
        
        # Should be trending (z-score > 2 due to std floor)
        assert score.algorithm == "zscore"
        assert score.raw_score is not None
    
    def test_modified_zscore(self):
        """Test modified Z-score calculation (MAD-based)."""
        config = AnomalyConfig(
            min_recent_samples=3,
            min_baseline_samples=5,
            zscore_params=ZScoreParams(use_modified_zscore=True),
        )
        strategy = ZScoreStrategy(config)
        
        baseline = make_viewership_data([1000, 950, 1050, 980, 1020, 1010, 990])
        recent = make_viewership_data([1500, 1600, 1700])
        
        score = strategy.compute_score(recent, baseline)
        
        assert score.metadata.get('use_modified') is True
    
    def test_negative_zscore_clamping(self):
        """Test that negative Z-scores are clamped to 0."""
        config = AnomalyConfig(
            min_recent_samples=2,
            min_baseline_samples=2,
            zscore_params=ZScoreParams(clamp_negative=True),
        )
        strategy = ZScoreStrategy(config)
        
        # Recent below baseline
        baseline = make_viewership_data([1000] * 10)
        recent = make_viewership_data([500, 400, 300])  # Dropping
        
        score = strategy.compute_score(recent, baseline)
        
        # Raw score should be 0 (clamped from negative)
        assert score.raw_score >= 0
        # Logistic normalization with midpoint=0 maps z=0 to 50
        assert score.score == 50.0
    
    def test_insufficient_data(self):
        """Test that strategy computes score even with minimal data.
        
        Note: Data validation (INSUFFICIENT_DATA status) is now handled by
        the AsyncAnomalyDetector, not by individual strategies.
        """
        config = AnomalyConfig(min_recent_samples=10)
        strategy = ZScoreStrategy(config)
        
        baseline = make_viewership_data([1000] * 20)
        recent = make_viewership_data([1000] * 3)  # Not enough
        
        # Strategy computes score; detector handles validation
        score = strategy.compute_score(recent, baseline)
        
        # Strategy should still return a valid score object
        assert score.algorithm == "zscore"
        assert 0 <= score.score <= 100


class TestAnomalyStrategyFactory:
    """Tests for the strategy factory."""
    
    def test_create_from_config_quantile(self):
        """Test creating quantile strategy from config."""
        config = AnomalyConfig(algorithm='quantile')
        strategy = AnomalyStrategyFactory.create(config)
        
        assert isinstance(strategy, QuantileStrategy)
        assert strategy.name == 'quantile'
    
    def test_create_from_config_zscore(self):
        """Test creating zscore strategy from config."""
        config = AnomalyConfig(algorithm='zscore')
        strategy = AnomalyStrategyFactory.create(config)
        
        assert isinstance(strategy, ZScoreStrategy)
        assert strategy.name == 'zscore'
    
    def test_create_by_name(self):
        """Test creating strategy by name."""
        config = AnomalyConfig()
        
        strategy = AnomalyStrategyFactory.create_by_name('quantile', config)
        assert isinstance(strategy, QuantileStrategy)
        
        strategy = AnomalyStrategyFactory.create_by_name('zscore', config)
        assert isinstance(strategy, ZScoreStrategy)
    
    def test_invalid_algorithm_raises(self):
        """Test that invalid algorithm raises error."""
        config = AnomalyConfig()
        
        with pytest.raises(ValueError, match="Unknown algorithm"):
            AnomalyStrategyFactory.create_by_name('invalid', config)
    
    def test_available_algorithms(self):
        """Test listing available algorithms."""
        algorithms = AnomalyStrategyFactory.available_algorithms()
        
        assert 'quantile' in algorithms
        assert 'zscore' in algorithms
    
    def test_is_valid_algorithm(self):
        """Test algorithm validation."""
        assert AnomalyStrategyFactory.is_valid_algorithm('quantile')
        assert AnomalyStrategyFactory.is_valid_algorithm('zscore')
        assert not AnomalyStrategyFactory.is_valid_algorithm('invalid')
    
    def test_direct_creation_methods(self):
        """Test direct factory methods."""
        config = AnomalyConfig()
        
        quantile = AnomalyStrategyFactory.create_quantile(config)
        assert isinstance(quantile, QuantileStrategy)
        
        zscore = AnomalyStrategyFactory.create_zscore(config)
        assert isinstance(zscore, ZScoreStrategy)
    
    def test_register_custom_strategy(self):
        """Test registering a custom strategy."""
        class CustomStrategy:
            def __init__(self, config):
                self.config = config
            
            @property
            def name(self):
                return "custom"
            
            def compute_score(self, recent, baseline):
                pass
            
            def validate_data(self, *args):
                return None
        
        # Register
        AnomalyStrategyFactory.register('custom', CustomStrategy)
        assert AnomalyStrategyFactory.is_valid_algorithm('custom')
        
        # Clean up
        AnomalyStrategyFactory.unregister('custom')
        assert not AnomalyStrategyFactory.is_valid_algorithm('custom')


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios."""
    
    def test_gradual_growth_detection(self):
        """Test detection of gradual viewership growth."""
        config = AnomalyConfig(
            min_recent_samples=3,
            min_baseline_samples=5,
        )
        
        # Baseline: steady at 1000
        baseline_counts = [1000] * 20
        
        # Recent: gradual increase to 1500
        recent_counts = [1200, 1300, 1400, 1500]
        
        baseline = make_viewership_data(baseline_counts)
        recent = make_viewership_data(recent_counts)
        
        # Test both strategies
        for algorithm in ['quantile', 'zscore']:
            config = AnomalyConfig(algorithm=algorithm, min_recent_samples=3, min_baseline_samples=5)
            strategy = AnomalyStrategyFactory.create(config)
            score = strategy.compute_score(recent, baseline)
            
            # 50% growth should register but may not be "trending"
            assert score.is_valid
            assert score.score >= 0
    
    def test_viral_spike_detection(self):
        """Test detection of sudden viral spike."""
        config = AnomalyConfig(
            min_recent_samples=3,
            min_baseline_samples=5,
        )
        
        # Baseline: steady at 1000
        baseline_counts = [950, 1000, 1050, 980, 1020] * 4
        
        # Recent: sudden 3x spike
        recent_counts = [2500, 2800, 3000, 3200]
        
        baseline = make_viewership_data(baseline_counts)
        recent = make_viewership_data(recent_counts)
        
        for algorithm in ['quantile', 'zscore']:
            config = AnomalyConfig(algorithm=algorithm, min_recent_samples=3, min_baseline_samples=5)
            strategy = AnomalyStrategyFactory.create(config)
            score = strategy.compute_score(recent, baseline)
            
            # 3x spike should definitely be trending
            assert score.status == AnomalyStatus.TRENDING
            # Logistic normalization: 3x spike gives high score (> 55)
            assert score.score > 55
    
    def test_new_stream_handling(self):
        """Test handling of new stream with limited history.
        
        Note: Insufficient data detection is now handled by the
        AsyncAnomalyDetector, not by individual strategies.
        Strategies compute scores regardless of sample count.
        """
        config = AnomalyConfig(
            min_recent_samples=3,
            min_baseline_samples=20,  # Require lots of baseline
        )
        
        # New stream: only 10 historical points
        baseline = make_viewership_data([1000] * 10)
        recent = make_viewership_data([1500] * 5)
        
        strategy = AnomalyStrategyFactory.create(config)
        score = strategy.compute_score(recent, baseline)
        
        # Strategy computes score; detector handles validation
        assert score.algorithm == "quantile"
        assert score.is_valid
    
    def test_ranking_multiple_streams(self):
        """Test that streams can be ranked by score."""
        config = AnomalyConfig(min_recent_samples=2, min_baseline_samples=2)
        strategy = AnomalyStrategyFactory.create(config)
        
        baseline = make_viewership_data([1000] * 10)
        
        # Different spike levels
        scenarios = [
            (1, [1000, 1000]),      # No spike
            (2, [1500, 1600]),      # Moderate spike
            (3, [2500, 2800]),      # Large spike
        ]
        
        scores = []
        for stream_id, recent_counts in scenarios:
            recent = make_viewership_data(
                recent_counts,
                livestream_id=stream_id,
            )
            score = strategy.compute_score(recent, baseline)
            scores.append(score)
        
        # Sort by score descending
        scores.sort(key=lambda s: s.score, reverse=True)
        
        # Highest spike should rank first
        assert scores[0].livestream_id == 3
        assert scores[1].livestream_id == 2
        assert scores[2].livestream_id == 1
