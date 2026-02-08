# Anomaly Detection Module

## Overview

This module provides a modular anomaly detection system for identifying "trending" YouTube livestreams based on viewership spikes. It uses the **Strategy Pattern** to enable swappable detection algorithms.

## Architecture

```
app/anomaly/
├── __init__.py          # Public API exports
├── config.py            # Configuration dataclasses
├── protocol.py          # Strategy interface (Protocol)
├── quantile_strategy.py # Quantile-based algorithm
├── zscore_strategy.py   # Z-score based algorithm
├── logistic.py          # Logistic normalization functions
├── factory.py           # Strategy factory
└── detector.py          # High-level orchestration
```

### Key Design Decisions

1. **Strategy Pattern**: Algorithms are interchangeable via the `AnomalyStrategy` protocol
2. **Logistic Normalization**: All raw scores are normalized using a sigmoid function for consistent 0-100 output
3. **Centralized Validation**: Data validation (insufficient data, inactive streams) is handled by `AsyncAnomalyDetector`, not individual strategies

## Quick Start

```python
from sqlalchemy.orm import Session
from app.anomaly import AnomalyConfig, AnomalyDetector

# Create detector with default config (quantile algorithm)
with Session(engine) as session:
    detector = AnomalyDetector(session)
    
    # Get ranked list of trending streams
    rankings = detector.detect_all_live_streams()
    
    for score in rankings[:10]:
        print(f"{score.youtube_video_id}: {score.score:.1f} ({score.status})")
```

## Configuration

```python
from app.anomaly import AnomalyConfig, QuantileParams, ZScoreParams

# Default configuration
config = AnomalyConfig()

# Custom configuration
config = AnomalyConfig(
    recent_window_minutes=30,    # Compare last 30 minutes
    baseline_hours=48,           # Against last 48 hours
    algorithm='zscore',          # Use Z-score algorithm
    min_recent_samples=5,        # Need at least 5 recent data points
    min_baseline_samples=20,     # Need at least 20 baseline points
)

# Algorithm-specific tuning
config = AnomalyConfig(
    algorithm='quantile',
    quantile_params=QuantileParams(
        baseline_percentile=75.0,  # Use 75th percentile as baseline
        recent_percentile=90.0,    # Use 90th percentile for current
        spike_threshold=2.0,       # 2x baseline = trending
    ),
)
```

---

## Algorithm Details

### 1. Quantile-Based Detection (Default)

The quantile method compares percentiles of recent viewership against historical baseline. It's **robust to outliers** and handles skewed distributions well.

#### Mathematical Formulation

Given:
- $B = \{b_1, b_2, ..., b_n\}$ — baseline viewership values (last 24-48 hours)
- $R = \{r_1, r_2, ..., r_m\}$ — recent viewership values (last 15-30 minutes)

**Step 1: Compute Baseline Reference**
$$P_{baseline} = \text{percentile}(B, 75)$$

The 75th percentile represents the "expected high" viewership level.

**Step 2: Compute Recent State**
$$P_{recent} = \text{percentile}(R, 90)$$

The 90th percentile is used for robustness against momentary spikes/drops.

**Step 3: Calculate Spike Ratio**
$$\text{spike\_ratio} = \frac{P_{recent}}{P_{baseline}}$$

**Step 4: Determine Trend Status**
$$\text{status} = \begin{cases} \text{TRENDING} & \text{if spike\_ratio} \geq 1.5 \\ \text{NORMAL} & \text{otherwise} \end{cases}$$

**Step 5: Apply Logistic Normalization (0-100)**

The raw spike ratio is normalized using a logistic (sigmoid) function:

$$\text{score} = \text{min} + \frac{\text{max} - \text{min}}{1 + e^{-k(\text{ratio} - m)}}$$

Where:
- $k = 0.1$ — steepness of the sigmoid curve
- $m = 0$ — midpoint (ratio of 0 maps to score 50)
- min/max from `AnomalyConfig.score_min` and `score_max`

This provides:
- Smooth S-curve mapping that compresses extreme values
- Good resolution in the middle range
- Scores centered at 50 for "normal" ratios around 1.0

#### Why Quantiles?

| Advantage | Explanation |
|-----------|-------------|
| Outlier resistance | A single viral moment won't skew the baseline |
| Distribution agnostic | Works for normal, log-normal, and multimodal data |
| Interpretable | "Current 90th percentile is 2x the historical 75th" |
| Tunable | Adjust percentiles for sensitivity |

#### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `baseline_percentile` | 75.0 | Historical reference point |
| `recent_percentile` | 90.0 | Current state measurement |
| `spike_threshold` | 1.5 | Minimum ratio for "trending" |
| `high_traffic_multiplier` | 1.2 | Boost for high-traffic streams |

---

### 2. Z-Score Based Detection

The Z-score method measures how many **standard deviations** the current viewership is from the historical mean.

#### Standard Z-Score

$$z = \frac{x - \mu}{\sigma}$$

Where:
- $x$ = current viewership (90th percentile of recent window)
- $\mu$ = mean of baseline viewership
- $\sigma$ = standard deviation of baseline viewership

**Interpretation:**
- $z = 0$: At the mean
- $z = 2$: 2 standard deviations above mean (~2.3% probability in normal distribution)
- $z = 3$: 3 standard deviations above mean (~0.1% probability)

#### Modified Z-Score (MAD-based) — Recommended

For robustness against outliers, the module supports **Modified Z-Score** using Median Absolute Deviation (MAD):

$$\text{MAD} = \text{median}(|x_i - \text{median}(X)|)$$

$$z_{modified} = 0.6745 \times \frac{x - \text{median}(B)}{\text{MAD}(B)}$$

The constant 0.6745 is the 75th percentile of the standard normal distribution, making MAD comparable to standard deviation for normally distributed data.

#### Why MAD-based Z-Score?

| Standard Z-Score | Modified Z-Score (MAD) |
|-----------------|----------------------|
| Sensitive to outliers | Robust to outliers |
| Mean can be skewed by viral moments | Median is stable |
| Better for normal distributions | Better for skewed distributions |

Livestream viewership is often **heavily skewed** (many streams have few viewers, some have millions), making MAD the preferred choice.

#### Normalization to 0-100 (Logistic Function)

Both algorithms use a logistic (sigmoid) function for score normalization:

$$\text{score} = \text{min} + \frac{\text{max} - \text{min}}{1 + e^{-k(x - m)}}$$

Where:
- $x$ = raw score (spike_ratio for Quantile, z-score for Z-Score)
- $k = 0.1$ — steepness of sigmoid (configurable)
- $m = 0$ — midpoint value that maps to 50

**Why Logistic Normalization?**
- Compresses extreme outliers smoothly
- Maintains good resolution in the middle range
- Continuous and differentiable
- Bounded output (always within [min, max])

This sigmoid normalization gives:
- Score = 50 when $x = m$ (midpoint)
- Score → max as $x \to +\infty$  
- Score → min as $x \to -\infty$

#### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `zscore_threshold` | 2.0 | Z-score to be considered trending |
| `use_modified_zscore` | True | Use MAD instead of std dev |
| `min_std_floor` | 10.0 | Minimum std dev (prevents div-by-zero) |
| `clamp_negative` | True | Ignore below-mean viewership |

---

## Comparing the Algorithms

| Aspect | Quantile | Z-Score |
|--------|----------|---------|
| **Best for** | Skewed distributions | Near-normal distributions |
| **Outlier handling** | Excellent | Good (with MAD) |
| **Interpretability** | High ("2x the normal high") | Medium ("2σ above mean") |
| **Sensitivity** | Moderate | Higher |
| **Computation** | O(n log n) for percentile | O(n) for mean/std |

**Recommendation:** Start with **Quantile** (default) for most use cases. Use **Z-Score** if you need finer sensitivity or your data is normally distributed.

---

## Edge Cases

### 1. New Streams (Insufficient History)

If a stream has fewer data points than `min_baseline_samples`, it receives:
- Status: `INSUFFICIENT_DATA`
- Score: 0

**Rationale:** Without sufficient history, we can't establish a reliable baseline.

### 2. Inactive Streams

A stream is marked `INACTIVE` if:
- Recent median viewership is 0
- Recent viewership dropped to <1% of baseline

### 3. Zero Standard Deviation

When baseline viewership is perfectly constant:
- A `min_std_floor` (default 10) is applied
- Prevents division by zero
- Ensures even small variations are detected

### 4. Negative Anomaly Scores

Below-average viewership produces negative Z-scores. By default, these are clamped to 0 since we only care about **spikes** (trending up), not drops.

---

## Performance Considerations

The system is designed for **100+ streams** with efficient batch processing:

1. **Single Query per Stream:** Fetches all historical data in one database query
2. **Vectorized Computation:** Uses NumPy for fast percentile/mean calculations
3. **Index Optimization:** Relies on `idx_viewership_anomaly_detection` composite index

**Time Complexity:**
- Per stream: O(n log n) where n = baseline samples
- Total: O(s × n log n) where s = number of streams

For 100 streams with 24 hours of 2-minute samples (720 points each):
- ~72,000 total data points
- Processing time: <1 second on modern hardware

---

## Extending with Custom Strategies

The Factory pattern allows adding new algorithms:

```python
from app.anomaly import AnomalyStrategyFactory, AnomalyConfig

class MovingAverageStrategy:
    def __init__(self, config: AnomalyConfig):
        self.config = config
    
    @property
    def name(self) -> str:
        return "moving_average"
    
    def compute_score(self, recent_data, baseline_data):
        # Your custom algorithm here
        ...
    
    def validate_data(self, recent, baseline, min_recent, min_baseline):
        # Validation logic
        ...

# Register the custom strategy
AnomalyStrategyFactory.register('moving_average', MovingAverageStrategy)

# Use it
config = AnomalyConfig(algorithm='moving_average')
strategy = AnomalyStrategyFactory.create(config)
```

---

## API Reference

### Main Classes

| Class | Purpose |
|-------|---------|
| `AnomalyConfig` | Configuration for detection |
| `AnomalyDetector` | High-level orchestration |
| `AsyncAnomalyDetector` | Async orchestration for FastAPI |
| `AnomalyStrategyFactory` | Strategy creation |
| `AnomalyScore` | Detection result container |
| `ViewershipData` | Time-series data container |

### Strategies

| Strategy | Config Key | Description |
|----------|------------|-------------|
| `QuantileStrategy` | `'quantile'` | Percentile-based detection |
| `ZScoreStrategy` | `'zscore'` | Standard deviation-based detection |

### Logistic Normalization Functions

```python
from app.anomaly import logistic_normalize, logistic_normalize_batch, inverse_logistic

# Normalize a single score
score = logistic_normalize(spike_ratio, config, midpoint=0.0, steepness=0.1)

# Normalize a batch
scores = logistic_normalize_batch([1.0, 1.5, 2.0, 3.0], config)

# Inverse operation (recover raw score from normalized)
raw = inverse_logistic(75.0, config)
```

| Function | Purpose |
|----------|---------|
| `logistic_normalize` | Apply sigmoid normalization to a single score |
| `logistic_normalize_batch` | Normalize a list of scores |
| `inverse_logistic` | Recover raw score from normalized value |

### Status Codes

| Status | Meaning |
|--------|---------|
| `NORMAL` | Viewership within expected range |
| `TRENDING` | Viewership spike detected |
| `INSUFFICIENT_DATA` | Not enough data points |
| `INACTIVE` | Stream appears offline |
| `ERROR` | Detection failed |
