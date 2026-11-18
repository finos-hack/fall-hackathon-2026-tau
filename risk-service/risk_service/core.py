"""Calculation core: filtered historical simulation VaR, backtest and verdict (spec M2-M7).

Implements contracts/calculation-api.md. Every function is pure: no files, network or clock.
Python 3.9+, standard library only. Day numbers follow the spec: a closes list holds C_0 ... C_N,
a P&L list holds x_1 ... x_N (so pnl[s-1] is x_s), and outputs are dicts keyed by day s or t.
The service runs on SYNTHETIC price history (seed 20261117), not real market data.
"""
import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence

KUPIEC_CRITICAL_5PCT = 3.841458820694124  # chi-square(1) 95% quantile


@dataclass(frozen=True)
class Params:
    lam: float = 0.94
    pool: int = 250  # n
    warmup: int = 100  # W
    p: float = 0.01


class ZeroVolatilityError(ValueError):
    """sigma^2_{W+1} == 0: every warm-up P&L value is zero (spec M3)."""


class InsufficientHistoryError(ValueError):
    """len(pnl) < W + n (contract: var_forecasts, backtest)."""


@dataclass(frozen=True)
class BacktestRow:
    t: int
    forecast_var: float
    pnl: float
    breach: bool  # pnl < -forecast_var, unrounded


@dataclass(frozen=True)
class Backtest:
    rows: list  # list[BacktestRow], t ascending, length N - W - n
    current_var: float  # forecast for day N+1


@dataclass(frozen=True)
class Kupiec:
    lr: float
    p_value: float
    reject: bool  # lr > 3.841458820694124
    direction: Optional[str]  # "too_many" | "too_few" when reject, else None


def pnl_series(closes: Mapping[str, Sequence[float]], positions: Mapping[str, float]) -> List[float]:
    """x_1 ... x_N with x_s = sum_i q_i (P_i,s - P_i,s-1), summed in ascending ticker order (M2)."""
    lengths = {len(series) for series in closes.values()}
    if len(lengths) != 1:
        raise ValueError("all close lists must have the same length")
    length = lengths.pop()
    if length < 2:
        raise ValueError("close lists need at least two values (C_0 and C_1)")
    tickers = sorted(positions)
    for ticker in tickers:
        if ticker not in closes:
            raise KeyError(ticker)
    pnl = []
    for s in range(1, length):
        total = 0.0
        for ticker in tickers:
            series = closes[ticker]
            total += positions[ticker] * (series[s] - series[s - 1])
        pnl.append(total)
    return pnl


def ewma_sigmas(pnl: Sequence[float], params: Params) -> Dict[int, float]:
    """sigma_s for s = W+1 ... N+1 (M3). Seed: sigma^2_{W+1} = mean of x_1^2 ... x_W^2.
    Recursion: sigma^2_{s+1} = lam * sigma^2_s + (1 - lam) * x_s^2, so sigma_s uses x up to s-1."""
    w, lam = params.warmup, params.lam
    n_days = len(pnl)
    if w < 1 or n_days < w:
        raise InsufficientHistoryError(f"need at least W = {w} P&L values, got {n_days}")
    variance = sum(x * x for x in pnl[:w]) / w
    if variance == 0.0:
        raise ZeroVolatilityError("sigma^2_{W+1} is zero: every warm-up P&L value is zero")
    sigmas = {w + 1: math.sqrt(variance)}
    for s in range(w + 1, n_days + 1):
        x = pnl[s - 1]
        variance = lam * variance + (1.0 - lam) * (x * x)
        sigmas[s + 1] = math.sqrt(variance)
    return sigmas


def residuals(pnl: Sequence[float], params: Params) -> Dict[int, float]:
    """z_s = x_s / sigma_s for s = W+1 ... N (M3)."""
    sigmas = ewma_sigmas(pnl, params)
    return {s: pnl[s - 1] / sigmas[s] for s in range(params.warmup + 1, len(pnl) + 1)}


def interp_quantile(values: Sequence[float], p: float) -> float:
    """M4: sort ascending, h = (n-1)p, k = floor(h), w = h - k,
    Q = z_(k+1) + w (z_(k+2) - z_(k+1)) with 1-based order statistics; Q = z_(k+1) when k+2 > n."""
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        raise ValueError("interp_quantile needs at least one value")
    h = (n - 1) * p
    k = math.floor(h)
    w = h - k
    if k + 2 > n:
        return ordered[k]
    return ordered[k] + w * (ordered[k + 1] - ordered[k])


def _check_history(pnl: Sequence[float], params: Params) -> None:
    if len(pnl) < params.warmup + params.pool:
        raise InsufficientHistoryError(
            f"need N >= W + n = {params.warmup + params.pool} P&L values, got {len(pnl)}"
        )


def var_forecasts(pnl: Sequence[float], params: Params) -> Dict[int, float]:
    """VaR_t = -sigma_t * Q(z_{t-n} ... z_{t-1}) for t = W+n+1 ... N+1 (M5). No flooring.
    The forecast for day t depends only on x_1 ... x_{t-1} (no look-ahead, FR-012)."""
    _check_history(pnl, params)
    sigmas = ewma_sigmas(pnl, params)
    z = residuals(pnl, params)
    n = params.pool
    forecasts = {}
    for t in range(params.warmup + n + 1, len(pnl) + 2):
        pool = [z[s] for s in range(t - n, t)]
        forecasts[t] = -sigmas[t] * interp_quantile(pool, params.p)
    return forecasts


def backtest(pnl: Sequence[float], params: Params) -> Backtest:
    """Rows for t = W+n+1 ... N (ascending), breach = x_t < -VaR_t unrounded, plus the
    current VaR = the forecast for N+1 (M5, FR-005)."""
    forecasts = var_forecasts(pnl, params)
    n_days = len(pnl)
    rows = []
    for t in range(params.warmup + params.pool + 1, n_days + 1):
        forecast = forecasts[t]
        realised = pnl[t - 1]
        rows.append(BacktestRow(t=t, forecast_var=forecast, pnl=realised, breach=realised < -forecast))
    return Backtest(rows=rows, current_var=forecasts[n_days + 1])


def _x_ln_y(x: float, y: float) -> float:
    """x * ln(y) with the convention 0 * ln 0 = 0."""
    return 0.0 if x == 0 else x * math.log(y)


def kupiec(breaches: int, T: int, p: float) -> Kupiec:
    """M6: LR = -2[(T-x)ln(1-p) + x ln p - (T-x)ln(1-x/T) - x ln(x/T)], 0 ln 0 = 0;
    p-value = erfc(sqrt(LR/2)); reject when LR > 3.841458820694124."""
    x = breaches
    rate = x / T
    lr = -2.0 * (_x_ln_y(T - x, 1.0 - p) + _x_ln_y(x, p) - _x_ln_y(T - x, 1.0 - rate) - _x_ln_y(x, rate))
    p_value = math.erfc(math.sqrt(max(lr, 0.0) / 2.0))
    reject = lr > KUPIEC_CRITICAL_5PCT
    direction = None
    if reject:
        if x > T * p:
            direction = "too_many"
        elif x < T * p:
            direction = "too_few"
    return Kupiec(lr=lr, p_value=p_value, reject=reject, direction=direction)


def basel_zone(breaches: int) -> str:
    """Basel traffic light for 250 observations (FR-007): green 0-4, amber 5-9, red >= 10."""
    if breaches <= 4:
        return "green"
    if breaches <= 9:
        return "amber"
    return "red"


def finite_sample_rate(n: int, p: float) -> float:
    """M7: (k+1+w)/(n+1) with h = (n-1)p, k = floor(h), w = h - k."""
    h = (n - 1) * p
    k = math.floor(h)
    w = h - k
    return (k + 1 + w) / (n + 1)
