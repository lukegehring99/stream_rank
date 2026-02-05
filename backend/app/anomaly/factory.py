"""Factory for creating anomaly detection strategies."""
from typing import Literal, Union

from .config import AnomalyConfig
from .interface import AnomalyStrategy
from .quantile import QuantileStrategy
from .zscore import ZScoreStrategy


AnomalyStrategyType = Literal["quantile", "zscore"]


def get_anomaly_strategy(
    config: AnomalyConfig = None,
    strategy_type: AnomalyStrategyType = None,
) -> AnomalyStrategy:
    """Get an anomaly detection strategy instance.
    
    Args:
        config: Full anomaly configuration (optional)
        strategy_type: Override strategy type (optional)
        
    Returns:
        Configured anomaly strategy instance
    """
    if config is None:
        config = AnomalyConfig()
    
    # Use override or config value
    algo = strategy_type or config.algorithm
    
    if algo == "quantile":
        return QuantileStrategy(params=config.quantile_params)
    elif algo == "zscore":
        return ZScoreStrategy(params=config.zscore_params)
    else:
        raise ValueError(f"Unknown anomaly strategy: {algo}")


def register_strategy(name: str, strategy_class: type) -> None:
    """Register a custom anomaly detection strategy.
    
    This allows extending the system with new algorithms without
    modifying the factory code.
    
    Usage:
        class MyCustomStrategy:
            def calculate_score(self, recent, baseline):
                # Custom logic
                return score, debug_info
            
            @property
            def name(self):
                return "custom"
        
        register_strategy("custom", MyCustomStrategy)
    """
    # Note: In a production system, this would update a registry dict
    # For now, strategies are hardcoded in get_anomaly_strategy
    raise NotImplementedError(
        "Custom strategy registration not yet implemented. "
        "Modify the factory function directly."
    )
