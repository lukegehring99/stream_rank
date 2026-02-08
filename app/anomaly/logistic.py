"""
Logistic Normalization
======================

Applies logistic (sigmoid) normalization to anomaly scores.
This provides a smooth S-curve mapping that compresses extreme values
while maintaining good resolution in the middle range.
"""

import math
from typing import Union

from app.anomaly.config import AnomalyConfig


def logistic_normalize(
    score: float,
    config: AnomalyConfig
) -> float:
    """
    Apply logistic (sigmoid) normalization to a score.
    
    The logistic function maps any real number to the range [score_min, score_max]
    using an S-curve. This is useful for:
    - Compressing extreme outliers
    - Maintaining resolution in the middle range
    - Providing smooth, continuous normalization
    
    The formula is:
        normalized = min + (max - min) / (1 + exp(-steepness * (score - midpoint)))
    
    Args:
        score: The raw score to normalize.
        config: AnomalyConfig containing score_min and score_max.
        midpoint: The score value that maps to the center of the output range.
            Default 0.0 means a raw score of 0 maps to (min+max)/2.
        steepness: Controls how steep the S-curve is. Higher values create
            sharper transitions. Default 0.1 provides a gentle curve.
            
    Returns:
        The normalized score in the range [config.score_min, config.score_max].
        
    Example:
        >>> config = AnomalyConfig(score_min=0, score_max=100)
        >>> logistic_normalize(0, config)  # midpoint -> 50
        50.0
        >>> logistic_normalize(50, config)  # high score -> ~99.3
        99.33...
        >>> logistic_normalize(-50, config)  # low score -> ~0.67
        0.669...
    """
    score_range = config.score_max - config.score_min
    midpoint = config.logistic_midpoint
    steepness = config.logistic_steepness

    
    # Handle edge case of zero range
    if score_range == 0:
        return config.score_min
    
    # Apply logistic function
    try:
        exponent = -steepness * (score - midpoint)
        # Clamp exponent to prevent overflow
        exponent = max(-700, min(700, exponent))
        sigmoid = 1.0 / (1.0 + math.exp(exponent))
    except OverflowError:
        # If exponent is very large negative, sigmoid -> 1
        # If exponent is very large positive, sigmoid -> 0
        sigmoid = 0.0 if exponent > 0 else 1.0
    
    return config.score_min + score_range * sigmoid


def logistic_normalize_batch(
    scores: list[float],
    config: AnomalyConfig
) -> list[float]:
    """
    Apply logistic normalization to a batch of scores.
    
    Args:
        scores: List of raw scores to normalize.
        config: AnomalyConfig containing score_min and score_max.
        midpoint: The score value that maps to the center of the output range.
        steepness: Controls how steep the S-curve is.
        
    Returns:
        List of normalized scores in the range [config.score_min, config.score_max].
    """
    return [
        logistic_normalize(score, config)
        for score in scores
    ]


def inverse_logistic(
    normalized: float,
    config: AnomalyConfig
) -> float:
    """
    Compute the inverse of logistic normalization.
    
    Given a normalized score, returns the original raw score.
    
    Args:
        normalized: A normalized score in [config.score_min, config.score_max].
        config: AnomalyConfig containing score_min and score_max.
        
    Returns:
        The original raw score before normalization.
        
    Raises:
        ValueError: If normalized is outside [score_min, score_max] or at boundaries.
    """
    score_range = config.score_max - config.score_min
    midpoint = config.logistic_midpoint
    steepness = config.logistic_steepness
    
    if score_range == 0:
        return midpoint
    
    # Convert to sigmoid value (0 to 1)
    sigmoid = (normalized - config.score_min) / score_range
    
    # Clamp to avoid math domain errors
    epsilon = 1e-10
    sigmoid = max(epsilon, min(1 - epsilon, sigmoid))
    
    # Inverse sigmoid: x = -ln((1/y) - 1)
    raw = midpoint - (1.0 / steepness) * math.log((1.0 / sigmoid) - 1)
    
    return raw
