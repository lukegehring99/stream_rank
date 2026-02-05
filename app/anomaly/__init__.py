"""
Anomaly Detection Module
========================

Modular anomaly detection system for identifying trending livestreams
based on viewership spikes using the Strategy pattern.

Example Usage:
    # Sync detection
    from app.anomaly import (
        AnomalyConfig,
        AnomalyStrategyFactory,
        detect_anomalies,
    )
    
    # Create configuration
    config = AnomalyConfig(
        recent_window_minutes=15,
        baseline_hours=24,
        algorithm='quantile',
    )
    
    # Get strategy
    strategy = AnomalyStrategyFactory.create(config)
    
    # Detect anomalies (sync)
    scores = detect_anomalies(session, strategy, config)
    
    # Async detection (FastAPI)
    from app.anomaly import AsyncAnomalyDetector
    
    async def get_trending(session: AsyncSession):
        detector = AsyncAnomalyDetector(session, config)
        return await detector.detect_all_live_streams()
"""

from app.anomaly.config import AnomalyConfig, QuantileParams, ZScoreParams
from app.anomaly.protocol import AnomalyStrategy, AnomalyScore, AnomalyStatus, ViewershipData
from app.anomaly.quantile_strategy import QuantileStrategy
from app.anomaly.zscore_strategy import ZScoreStrategy
from app.anomaly.factory import AnomalyStrategyFactory
from app.anomaly.detector import (
    AnomalyDetector,
    AsyncAnomalyDetector,
    detect_anomalies,
    detect_anomalies_async,
)

__all__ = [
    # Configuration
    'AnomalyConfig',
    'QuantileParams',
    'ZScoreParams',
    # Protocol & Data Types
    'AnomalyStrategy',
    'AnomalyScore',
    'AnomalyStatus',
    'ViewershipData',
    # Strategies
    'QuantileStrategy',
    'ZScoreStrategy',
    # Factory & Detector
    'AnomalyStrategyFactory',
    'AnomalyDetector',
    'AsyncAnomalyDetector',
    'detect_anomalies',
    'detect_anomalies_async',
]
