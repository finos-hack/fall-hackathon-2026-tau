#!/usr/bin/env python3
"""Generate the SYNTHETIC price history for feature 001 (spec.md, M1 and FR-014).

The output CSV, not this script, is authoritative. Random-number streams differ across languages
and library versions, so both implementations and all tests read the committed CSV and check it
against SHA256SUMS. This script exists so the file can be audited and reproduced.

Model (spec M1):
  - Calendar: 601 Monday-Friday dates (no holidays, synthetic) ending 2026-11-13.
  - Market factor: GARCH(1,1), alpha=0.08, beta=0.90, long-run daily vol 1.0%.
        omega = (1 - alpha - beta) * 0.01**2
        h_1 = 0.01**2 (start at the long-run variance)
        f_s = sqrt(h_s) * u_s
        h_{s+1} = omega + alpha * f_s**2 + beta * h_s
  - Ticker log return: r_{i,s} = 1.0 * f_s + 0.015 * e_{i,s}  (zero drift)
  - u_s and e_{i,s} are i.i.d. N(0,1).
  - Draw order from numpy.random.default_rng(20261117):
        first u (600 values, s = 1..600),
        then e (a 600 x 20 array in row-major order; columns follow the ticker order of the
        TraderX snapshot file).
  - Scaling: P_{i,s} = snapshot_close_i * exp(L_{i,s} - L_{i,600}), where L is the cumulative log
    return with L_{i,0} = 0. The close on the as-of date therefore equals the snapshot closePrice.
  - Rounding: closes are written with 4 decimal places. The rounded values in the CSV are the
    prices; there is no hidden unrounded series.

Usage (run from the repository root):
    python3 specs/001-portfolio-var-backtest/data/generate_synthetic_prices.py          # write files
    python3 specs/001-portfolio-var-backtest/data/generate_synthetic_prices.py --check  # regenerate in memory, compare
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys

import numpy as np

SEED = 20261117
AS_OF = dt.date(2026, 11, 13)
N_CLOSES = 601
ALPHA, BETA = 0.08, 0.90
LONG_RUN_DAILY_VOL = 0.01
LOADING = 1.0
IDIO_DAILY_VOL = 0.015
DECIMALS = 4

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
SNAPSHOT = REPO / "traderx" / "price-publisher" / "data" / "snapshot-prices.json"
CSV_NAME = "synthetic_prices_seed20261117.csv"
META_NAME = "synthetic_prices_seed20261117.meta.json"
SUMS_NAME = "SHA256SUMS"


def weekdays_ending(end: dt.date, count: int) -> list:
    days, d = [], end
    while len(days) < count:
        if d.weekday() < 5:
            days.append(d)
        d -= dt.timedelta(days=1)
    return days[::-1]


def build() -> tuple:
    snap = json.loads(SNAPSHOT.read_text())
    tickers = list(snap.keys())  # file order defines the column order and the draw order
    anchor = np.array([float(snap[t]["closePrice"]) for t in tickers])

    n_ret = N_CLOSES - 1
    rng = np.random.default_rng(SEED)
    u = rng.standard_normal(n_ret)
    e = rng.standard_normal((n_ret, len(tickers)))

    omega = (1.0 - ALPHA - BETA) * LONG_RUN_DAILY_VOL**2
    h = LONG_RUN_DAILY_VOL**2
    f = np.empty(n_ret)
    for s in range(n_ret):
        f[s] = np.sqrt(h) * u[s]
        h = omega + ALPHA * f[s] ** 2 + BETA * h

    r = LOADING * f[:, None] + IDIO_DAILY_VOL * e
    L = np.vstack([np.zeros(len(tickers)), np.cumsum(r, axis=0)])
    prices = anchor[None, :] * np.exp(L - L[-1][None, :])

    dates = weekdays_ending(AS_OF, N_CLOSES)
    lines = ["date," + ",".join(tickers)]
    for d, row in zip(dates, prices):
        lines.append(d.isoformat() + "," + ",".join(f"{p:.{DECIMALS}f}" for p in row))
    csv_bytes = ("\n".join(lines) + "\n").encode("ascii")

    # Sanity checks that the file matches M1.
    assert len(dates) == N_CLOSES and dates[-1] == AS_OF
    assert all(d.weekday() < 5 for d in dates)
    for j, t in enumerate(tickers):
        assert f"{prices[-1, j]:.{DECIMALS}f}" == f"{anchor[j]:.{DECIMALS}f}", t
    assert np.all(np.isfinite(prices)) and np.all(prices > 0)

    meta = {
        "label": "SYNTHETIC price history - not real market data",
        "synthetic": True,
        "feature": "001-portfolio-var-backtest",
        "spec_section": "M1",
        "seed": SEED,
        "rng": "numpy.random.default_rng (PCG64); draw order: u[600], then e[600,20] row-major",
        "numpy_version_used": np.__version__,
        "calendar": "Monday-Friday, no holidays (synthetic calendar)",
        "first_date": dates[0].isoformat(),
        "as_of_date": AS_OF.isoformat(),
        "n_closes": N_CLOSES,
        "tickers": tickers,
        "model": {
            "factor": "GARCH(1,1)",
            "alpha": ALPHA,
            "beta": BETA,
            "omega": omega,
            "long_run_daily_vol": LONG_RUN_DAILY_VOL,
            "h_initial": LONG_RUN_DAILY_VOL**2,
            "loading": LOADING,
            "idiosyncratic_daily_vol": IDIO_DAILY_VOL,
            "drift": 0.0,
            "innovations": "i.i.d. standard normal",
        },
        "anchor": "close on as_of_date equals traderx/price-publisher/data/snapshot-prices.json closePrice",
        "decimals": DECIMALS,
        "csv_file": CSV_NAME,
        "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "authoritative": "the CSV file; regenerating with another library version may differ",
    }
    meta_bytes = (json.dumps(meta, indent=2) + "\n").encode("ascii")
    return csv_bytes, meta_bytes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare a fresh build with the committed files")
    args = ap.parse_args()

    csv_bytes, meta_bytes = build()
    csv_hash = hashlib.sha256(csv_bytes).hexdigest()

    if args.check:
        on_disk = (HERE / CSV_NAME).read_bytes()
        ok = on_disk == csv_bytes
        print(f"regenerated sha256 {csv_hash}")
        print(f"committed   sha256 {hashlib.sha256(on_disk).hexdigest()}")
        print("MATCH" if ok else "MISMATCH")
        return 0 if ok else 1

    (HERE / CSV_NAME).write_bytes(csv_bytes)
    (HERE / META_NAME).write_bytes(meta_bytes)
    meta_hash = hashlib.sha256(meta_bytes).hexdigest()
    (HERE / SUMS_NAME).write_text(f"{csv_hash}  {CSV_NAME}\n{meta_hash}  {META_NAME}\n")
    print(f"wrote {CSV_NAME} sha256 {csv_hash}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
