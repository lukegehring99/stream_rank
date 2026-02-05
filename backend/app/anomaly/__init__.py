"""Anomaly detection module."""
from .config import AnomalyConfig, QuantileParams, ZScoreParams
from .interface import AnomalyStrategy, ViewershipData, AnomalyScore
from .quantile import QuantileStrategy
from .zscore import ZScoreStrategy
from .factory import get_anomaly_strategy, AnomalyStrategyType
from .detector import AnomalyDetector

__all__ = [
    # Config
    "AnomalyConfig",
    "QuantileParams",
    "ZScoreParams",
    # Interface
    "AnomalyStrategy",
    "ViewershipData",
    "AnomalyScore",
    # Strategies
    "QuantileStrategy",
    "ZScoreStrategy",
    # Factory
    "get_anomaly_strategy",
    "AnomalyStrategyType",
    # Detector
    "AnomalyDetector",
]
