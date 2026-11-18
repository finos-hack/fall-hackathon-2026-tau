"""Independent implementation of spec M2-M7 for oracle comparisons."""

from dataclasses import dataclass
from math import erfc, floor, log, sqrt
from typing import Dict, Mapping, Optional, Sequence


@dataclass(frozen=True)
class Params:
    lam: float = 0.94
    pool: int = 250
    warmup: int = 100
    p: float = 0.01


class ZeroVolatilityError(ValueError):
    pass


class InsufficientHistoryError(ValueError):
    pass


@dataclass(frozen=True)
class BacktestRow:
    t: int
    forecast_var: float
    pnl: float
    breach: bool


@dataclass(frozen=True)
class Backtest:
    rows: list
    current_var: float


@dataclass(frozen=True)
class Kupiec:
    lr: float
    p_value: float
    reject: bool
    direction: Optional[str]


def pnl_series(
    closes: Mapping[str, Sequence[float]],
    positions: Mapping[str, float],
) -> list:
    """Compute constant-position daily dollar P&L (spec M2)."""
    if not closes:
        raise ValueError("closes must not be empty")

    lengths = {len(series) for series in closes.values()}
    if len(lengths) != 1 or next(iter(lengths)) < 2:
        raise ValueError("all close series must have the same length of at least two")

    for ticker in positions:
        if ticker not in closes:
            raise KeyError(ticker)

    close_count = next(iter(lengths))
    result = []
    for s in range(1, close_count):
        day_pnl = 0.0
        for ticker in sorted(positions):
            day_pnl += positions[ticker] * (
                closes[ticker][s] - closes[ticker][s - 1]
            )
        result.append(day_pnl)
    return result


def ewma_sigmas(pnl: Sequence[float], params: Params) -> Dict[int, float]:
    """Compute lagged EWMA standard deviations (spec M3)."""
    n_days = len(pnl)
    if n_days < params.warmup:
        raise InsufficientHistoryError("not enough observations for warm-up")

    variance = sum(value * value for value in pnl[: params.warmup]) / params.warmup
    if variance == 0.0:
        raise ZeroVolatilityError("warm-up volatility is zero")

    sigmas = {params.warmup + 1: sqrt(variance)}
    for s in range(params.warmup + 1, n_days + 1):
        variance = params.lam * variance + (1.0 - params.lam) * pnl[s - 1] ** 2
        sigmas[s + 1] = sqrt(variance)
    return sigmas


def residuals(pnl: Sequence[float], params: Params) -> Dict[int, float]:
    """Compute filtered residuals z_s (spec M3)."""
    sigmas = ewma_sigmas(pnl, params)
    return {
        s: pnl[s - 1] / sigmas[s]
        for s in range(params.warmup + 1, len(pnl) + 1)
    }


def interp_quantile(values: Sequence[float], p: float) -> float:
    """Compute the position-(n-1)p linearly interpolated quantile (spec M4)."""
    if not values:
        raise ValueError("quantile requires at least one value")

    ordered = sorted(values)
    h = (len(ordered) - 1) * p
    k = floor(h)
    weight = h - k
    quantile = ordered[k]
    if k + 1 < len(ordered):
        quantile += weight * (ordered[k + 1] - quantile)
    return quantile


def var_forecasts(pnl: Sequence[float], params: Params) -> Dict[int, float]:
    """Compute historical-simulation VaR forecasts through day N+1 (spec M5)."""
    n_days = len(pnl)
    if n_days < params.warmup + params.pool:
        raise InsufficientHistoryError("not enough observations for the residual pool")

    sigmas = ewma_sigmas(pnl, params)
    standardized = residuals(pnl, params)
    forecasts = {}
    for t in range(params.warmup + params.pool + 1, n_days + 2):
        pool = [standardized[s] for s in range(t - params.pool, t)]
        forecasts[t] = -sigmas[t] * interp_quantile(pool, params.p)
    return forecasts


def backtest(pnl: Sequence[float], params: Params) -> Backtest:
    """Create backtest rows and the following-day current VaR (spec M5)."""
    forecasts = var_forecasts(pnl, params)
    n_days = len(pnl)
    rows = []
    for t in range(params.warmup + params.pool + 1, n_days + 1):
        forecast = forecasts[t]
        realised = pnl[t - 1]
        rows.append(
            BacktestRow(
                t=t,
                forecast_var=forecast,
                pnl=realised,
                breach=realised < -forecast,
            )
        )
    return Backtest(rows=rows, current_var=forecasts[n_days + 1])


def kupiec(breaches: int, T: int, p: float) -> Kupiec:
    """Compute the unconditional-coverage statistic and its chi-square p-value (spec M6)."""
    observed_rate = breaches / T
    null_log_likelihood = (T - breaches) * log(1.0 - p)
    if breaches:
        null_log_likelihood += breaches * log(p)

    observed_log_likelihood = 0.0
    if T - breaches:
        observed_log_likelihood += (T - breaches) * log(1.0 - observed_rate)
    if breaches:
        observed_log_likelihood += breaches * log(observed_rate)

    lr = -2.0 * (null_log_likelihood - observed_log_likelihood)
    reject = lr > 3.841458820694124
    direction = None
    if reject:
        direction = "too_many" if breaches > T * p else "too_few"

    return Kupiec(
        lr=lr,
        p_value=erfc(sqrt(lr / 2.0)),
        reject=reject,
        direction=direction,
    )


def basel_zone(breaches: int) -> str:
    """Return the 250-observation Basel traffic-light zone (spec FR-007)."""
    if breaches <= 4:
        return "green"
    if breaches <= 9:
        return "amber"
    return "red"


def finite_sample_rate(n: int, p: float) -> float:
    """Compute the finite-sample quantile coverage approximation (spec M7)."""
    h = (n - 1) * p
    k = floor(h)
    weight = h - k
    return (k + 1 + weight) / (n + 1)
