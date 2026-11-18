# Contract: Calculation API (Python, pure functions)

This is the contract the validator's offline tests call: V1, V2, V4, V5, and the core of V3. Every
function is pure. None reads files, the network or the clock, so tests can pass their own prices,
P&L series and parameters (spec M1–M7).

- **Module**: `risk_service.core`
- **Import**: run from the repository root with `PYTHONPATH=risk-service`, e.g.
  `PYTHONPATH=risk-service python3 -m pytest tests/`.
- **Python**: 3.9 or later; standard library only.

## Indexing convention (applies to everything below)

- **Inputs are plain lists.** A closes list holds C₀ … C_N, so `closes[s]` is the close on day s.
  A P&L list holds x₁ … x_N, so `pnl[s-1]` is xₛ.
- **Outputs are keyed by the spec's day number s or t.** Keys use the spec's 1-based day numbers
  as `dict[int, float]`, so test code can use the spec formulas directly.
- **Series length sets everything.** N = `len(pnl)`. Backtest days are t = W+n+1 … N, so
  B = N − W − n, which may be 0. The current forecast is t = N+1. The service itself always has
  N = 600, B = 250.

## Types

```python
@dataclass(frozen=True)
class Params:
    lam: float = 0.94
    pool: int = 250      # n
    warmup: int = 100    # W
    p: float = 0.01

class ZeroVolatilityError(ValueError): ...      # sigma^2_{W+1} == 0
class InsufficientHistoryError(ValueError): ... # len(pnl) < W + n

@dataclass(frozen=True)
class BacktestRow:
    t: int
    forecast_var: float
    pnl: float
    breach: bool          # pnl < -forecast_var, unrounded

@dataclass(frozen=True)
class Backtest:
    rows: list            # list[BacktestRow], t ascending, length N - W - n
    current_var: float    # forecast for day N+1

@dataclass(frozen=True)
class Kupiec:
    lr: float
    p_value: float
    reject: bool          # lr > 3.841458820694124
    direction: Optional[str]  # "too_many" | "too_few" when reject, else None
```

## Functions

| Function | Returns | Spec |
|---|---|---|
| `pnl_series(closes: Mapping[str, Sequence[float]], positions: Mapping[str, float]) -> list[float]` | x₁ … x_N, where xₛ = Σᵢ qᵢ·(Pᵢ,ₛ − Pᵢ,ₛ₋₁), summed in ascending ticker order. All close lists must have equal length N+1 ≥ 2. Every position ticker must be in `closes` (otherwise `KeyError`). | M2 |
| `ewma_sigmas(pnl, params) -> dict[int, float]` | σₛ for s = W+1 … N+1. Raises `ZeroVolatilityError` if σ²_{W+1} = 0. | M3 |
| `residuals(pnl, params) -> dict[int, float]` | zₛ = xₛ/σₛ for s = W+1 … N | M3 |
| `interp_quantile(values: Sequence[float], p: float) -> float` | the M4 quantile of the values (unsorted input allowed) | M4 |
| `var_forecasts(pnl, params) -> dict[int, float]` | VaRₜ = −σₜ·Q(z_{t−n} … z_{t−1}) for t = W+n+1 … N+1. Raises `InsufficientHistoryError` if N < W+n. | M5 |
| `backtest(pnl, params) -> Backtest` | rows for t = W+n+1 … N, plus current_var | M5, FR-005 |
| `kupiec(breaches: int, T: int, p: float) -> Kupiec` | the M6 LR (0·ln 0 = 0) and p-value erfc(√(LR/2)) | M6 |
| `basel_zone(breaches: int) -> str` | "green" for 0–4, "amber" for 5–9, "red" for ≥10 (250 observations) | FR-007 |
| `finite_sample_rate(n: int, p: float) -> float` | (k+1+w)/(n+1) with h = (n−1)p, k = ⌊h⌋, w = h − k | M7 |

## Guarantees the tests may rely on

1. **No look-ahead (FR-012, V4)**: `var_forecasts(pnl, params)[t]` depends only on `pnl[:t-1]`, that
   is x₁ … x_{t−1}. Changing any xₛ with s ≥ t, or any close Cₛ with s ≥ t, leaves it bit-for-bit
   identical.
2. **Determinism (FR-013)**: the same inputs always give identical floats.
3. **Parameters are honoured**: λ, n, W and p are taken from `params`, never from constants. V1 uses
   `Params(lam=0.94, pool=5, warmup=2, p=0.01)`.
4. **Quantile edge**: when k+2 > n, Q = z₍ₖ₊₁₎.
5. **No flooring**: VaR is returned as computed, even if ≤ 0.

## V1 worked call (spec Verification Expectations)

```python
from risk_service.core import Params, pnl_series, backtest
closes = {"XYZ": [100, 101, 99, 100, 97, 98, 99, 96, 93]}
pnl = pnl_series(closes, {"XYZ": 10})          # [10, -20, 10, -30, 10, 10, -30, -30]
bt = backtest(pnl, Params(lam=0.94, pool=5, warmup=2, p=0.01))
# bt.rows == [BacktestRow(t=8, forecast_var≈33.3085, pnl=-30, breach=False)]
```
