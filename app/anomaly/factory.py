"""
Anomaly Detection Strategy Factory
==================================

Factory pattern implementation for creating anomaly detection strategies.
Centralizes strategy instantiation and provides runtime algorithm selection.

Design Pattern: Factory + Strategy
----------------------------------
The Factory pattern is combined with Strategy pattern to enable:
1. Decoupled algorithm selection from business logic
2. Easy addition of new algorithms without changing existing code
3. Configuration-driven algorithm switching
4. Type-safe strategy creation

Usage:
    from app.anomaly import AnomalyConfig, AnomalyStrategyFactory
    
    # Using config
    config = AnomalyConfig(algorithm='quantile')
    strategy = AnomalyStrategyFactory.create(config)
    
    # Direct creation
    strategy = AnomalyStrategyFactory.create_quantile(config)
    strategy = AnomalyStrategyFactory.create_zscore(config)
    
    # Get all available algorithms
    algorithms = AnomalyStrategyFactory.available_algorithms()
"""

from typing import Dict, Type, Callable

from app.anomaly.config import AnomalyConfig, AlgorithmType
from app.anomaly.protocol import AnomalyStrategy
from app.anomaly.quantile_strategy import QuantileStrategy
from app.anomaly.zscore_strategy import ZScoreStrategy


class AnomalyStrategyFactory:
    """
    Factory for creating anomaly detection strategies.
    
    Provides centralized strategy creation with support for:
    - Configuration-based selection
    - Direct algorithm specification
    - Strategy registration for extensibility
    
    Class Attributes:
        _strategies: Registry mapping algorithm names to strategy classes
    
    Example:
        # Recommended: Use config-based creation
        config = AnomalyConfig(algorithm='quantile')
        strategy = AnomalyStrategyFactory.create(config)
        
        # Alternative: Direct creation
        strategy = AnomalyStrategyFactory.create_by_name('zscore', config)
    """
    
    # Strategy registry
    _strategies: Dict[str, Type] = {
        'quantile': QuantileStrategy,
        'zscore': ZScoreStrategy,
    }
    
    @classmethod
    def create(cls, config: AnomalyConfig) -> AnomalyStrategy:
        """
        Create a strategy based on configuration.
        
        This is the primary factory method. It reads the algorithm
        setting from the config and instantiates the appropriate strategy.
        
        Args:
            config: Anomaly detection configuration with algorithm specified
        
        Returns:
            Configured strategy instance implementing AnomalyStrategy
        
        Raises:
            ValueError: If algorithm name is not recognized
        
        Example:
            config = AnomalyConfig(algorithm='quantile')
            strategy = AnomalyStrategyFactory.create(config)
            assert strategy.name == 'quantile'
        """
        return cls.create_by_name(config.algorithm, config)
    
    @classmethod
    def create_by_name(cls, algorithm: str, config: AnomalyConfig) -> AnomalyStrategy:
        """
        Create a strategy by algorithm name.
        
        Useful when algorithm selection comes from external input
        (API parameter, CLI argument, etc.)
        
        Args:
            algorithm: Algorithm name ('quantile', 'zscore')
            config: Anomaly detection configuration
        
        Returns:
            Configured strategy instance
        
        Raises:
            ValueError: If algorithm name is not recognized
        """
        algorithm = algorithm.lower().strip()
        
        if algorithm not in cls._strategies:
            available = ', '.join(cls._strategies.keys())
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. "
                f"Available algorithms: {available}"
            )
        
        strategy_class = cls._strategies[algorithm]
        return strategy_class(config=config)
    
    @classmethod
    def create_quantile(cls, config: AnomalyConfig) -> QuantileStrategy:
        """
        Create a quantile-based strategy.
        
        Convenience method for explicit quantile strategy creation.
        
        Args:
            config: Anomaly detection configuration
        
        Returns:
            QuantileStrategy instance
        """
        return QuantileStrategy(config=config)
    
    @classmethod
    def create_zscore(cls, config: AnomalyConfig) -> ZScoreStrategy:
        """
        Create a Z-score based strategy.
        
        Convenience method for explicit Z-score strategy creation.
        
        Args:
            config: Anomaly detection configuration
        
        Returns:
            ZScoreStrategy instance
        """
        return ZScoreStrategy(config=config)
    
    @classmethod
    def register(cls, name: str, strategy_class: Type) -> None:
        """
        Register a new strategy type.
        
        Enables extension with custom strategies without modifying
        the factory code.
        
        Args:
            name: Algorithm name for configuration
            strategy_class: Strategy class implementing AnomalyStrategy
        
        Raises:
            ValueError: If name already registered
            TypeError: If class doesn't implement AnomalyStrategy
        
        Example:
            class CustomStrategy:
                def __init__(self, config): ...
                @property
                def name(self): return "custom"
                def compute_score(self, recent, baseline): ...
                def validate_data(self, ...): ...
            
            AnomalyStrategyFactory.register('custom', CustomStrategy)
        """
        name = name.lower().strip()
        
        if name in cls._strategies:
            raise ValueError(f"Strategy '{name}' is already registered")
        
        # Basic validation that the class has required interface
        if not callable(getattr(strategy_class, 'compute_score', None)):
            raise TypeError(
                f"Strategy class must implement compute_score method"
            )
        
        cls._strategies[name] = strategy_class
    
    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Remove a registered strategy.
        
        Args:
            name: Algorithm name to remove
        
        Returns:
            True if removed, False if not found
        """
        name = name.lower().strip()
        
        if name in cls._strategies:
            del cls._strategies[name]
            return True
        return False
    
    @classmethod
    def available_algorithms(cls) -> list[str]:
        """
        Get list of available algorithm names.
        
        Returns:
            Sorted list of registered algorithm names
        """
        return sorted(cls._strategies.keys())
    
    @classmethod
    def is_valid_algorithm(cls, name: str) -> bool:
        """
        Check if an algorithm name is valid.
        
        Args:
            name: Algorithm name to check
        
        Returns:
            True if algorithm is registered
        """
        return name.lower().strip() in cls._strategies
    
    @classmethod
    def get_default_config(cls, algorithm: str = 'quantile') -> AnomalyConfig:
        """
        Get default configuration for an algorithm.
        
        Convenience method for getting sensible defaults.
        
        Args:
            algorithm: Algorithm name
        
        Returns:
            AnomalyConfig with algorithm set
        """
        if not cls.is_valid_algorithm(algorithm):
            algorithm = 'quantile'
        return AnomalyConfig(algorithm=algorithm)
