"""
Anomaly Detection Module
========================

Modular anomaly detection system for identifying trending livestreams
based on viewership spikes using the Strategy pattern.

Example Usage:
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
    
    # Detect anomalies
    scores = detect_anomalies(session, strategy, config)
"""

from app.anomaly.config import AnomalyConfig, QuantileParams, ZScoreParams
from app.anomaly.protocol import AnomalyStrategy, AnomalyScore, ViewershipData
from app.anomaly.quantile_strategy import QuantileStrategy
from app.anomaly.zscore_strategy import ZScoreStrategy
from app.anomaly.factory import AnomalyStrategyFactory
from app.anomaly.detector import AnomalyDetector, detect_anomalies

__all__ = [
    # Configuration
    'AnomalyConfig',
    'QuantileParams',
    'ZScoreParams',
    # Protocol & Data Types
    'AnomalyStrategy',
    'AnomalyScore',
    'ViewershipData',
    # Strategies
    'QuantileStrategy',
    'ZScoreStrategy',
    # Factory & Detector
    'AnomalyStrategyFactory',
    'AnomalyDetector',
    'detect_anomalies',
]
