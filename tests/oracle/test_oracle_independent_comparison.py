import csv
import os
from pathlib import Path

import pytest

from risk_service import core as service
import oracle_independent_var as oracle


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = (
    REPOSITORY_ROOT / "specs/001-portfolio-var-backtest/data"
)

SEEDED_ACCOUNTS = (
    (22214, {"C": -2000.0, "IBM": -100.0, "MS": 1000.0}),
    (52355, {"BAC": -2400.0}),
)


def _data_path():
    configured = Path(os.environ.get("RISK_DATA_DIR", str(DEFAULT_DATA_DIR)))
    if not configured.is_absolute():
        configured = REPOSITORY_ROOT / configured
    return configured / "synthetic_prices_seed20261117.csv"


def _published_closes():
    with _data_path().open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        tickers = [name for name in reader.fieldnames if name != "date"]
        closes = {ticker: [] for ticker in tickers}
        for row in reader:
            for ticker in tickers:
                closes[ticker].append(float(row[ticker]))
    return closes


@pytest.mark.parametrize("account_id,positions", SEEDED_ACCOUNTS)
def test_published_history_agrees_with_independent_implementation(
    account_id, positions
):
    closes = _published_closes()

    service_pnl = service.pnl_series(closes, positions)
    oracle_pnl = oracle.pnl_series(closes, positions)

    service_backtest = service.backtest(service_pnl, service.Params())
    oracle_backtest = oracle.backtest(oracle_pnl, oracle.Params())

    # spec V3: every current VaR agrees within $0.01.
    assert abs(service_backtest.current_var - oracle_backtest.current_var) <= 0.01

    # spec FR-004 and V3: each seeded account has 250 compared backtest days.
    assert len(service_backtest.rows) == 250
    # spec FR-004 and V3: each seeded account has 250 compared backtest days.
    assert len(oracle_backtest.rows) == 250

    for expected_day, service_row, oracle_row in zip(
        range(351, 601), service_backtest.rows, oracle_backtest.rows
    ):
        # contracts/calculation-api.md indexing convention: rows are ascending by day t.
        assert service_row.t == expected_day
        # contracts/calculation-api.md indexing convention: rows are ascending by day t.
        assert oracle_row.t == expected_day
        # spec V3 and SC-004: every backtest forecast agrees within $0.01.
        assert abs(service_row.forecast_var - oracle_row.forecast_var) <= 0.01
        # spec V3 and SC-004: breach flags are identical on all account-days.
        assert service_row.breach is oracle_row.breach

    service_breaches = sum(row.breach for row in service_backtest.rows)
    oracle_breaches = sum(row.breach for row in oracle_backtest.rows)

    # spec V3: verdict breach counts are identical.
    assert service_breaches == oracle_breaches

    service_kupiec = service.kupiec(service_breaches, T=250, p=0.01)
    oracle_kupiec = oracle.kupiec(oracle_breaches, T=250, p=0.01)

    # spec V3: Kupiec LR agrees within 1e-6.
    assert abs(service_kupiec.lr - oracle_kupiec.lr) <= 1e-6
    # spec V3: Kupiec p-value agrees within 1e-6.
    assert abs(service_kupiec.p_value - oracle_kupiec.p_value) <= 1e-6
    # spec V3: verdict rejection decisions are identical.
    assert service_kupiec.reject is oracle_kupiec.reject
    # spec V3: verdict rejection directions are identical.
    assert service_kupiec.direction == oracle_kupiec.direction
    # spec V3: Basel verdict fields are identical.
    assert service.basel_zone(service_breaches) == oracle.basel_zone(oracle_breaches)
    # spec V3 and M7: finite-sample verdict rates are identical.
    assert service.finite_sample_rate(250, 0.01) == oracle.finite_sample_rate(
        250, 0.01
    )
