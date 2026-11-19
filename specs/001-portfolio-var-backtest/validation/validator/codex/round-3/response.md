```python file=tests/integration/test_integration_http_contract.py
import csv
import importlib.util
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RISK_BASE_URL = os.environ.get("RISK_BASE_URL", "http://127.0.0.1:18110").rstrip("/")
TRADERX_BASE_URL = os.environ.get(
    "TRADERX_BASE_URL", "http://127.0.0.1:8080"
).rstrip("/")
DATA_DIR = Path(
    os.environ.get(
        "RISK_DATA_DIR",
        str(REPOSITORY_ROOT / "specs/001-portfolio-var-backtest/data"),
    )
)
if not DATA_DIR.is_absolute():
    DATA_DIR = REPOSITORY_ROOT / DATA_DIR

DATA_FILE = DATA_DIR / "synthetic_prices_seed20261117.csv"
BASELINE_FILE = (
    REPOSITORY_ROOT
    / "specs/001-portfolio-var-backtest/validation/runs/baseline-before.json"
)
ORACLE_FILE = REPOSITORY_ROOT / "tests/oracle/oracle_independent_var.py"

EXPECTED_SHA256 = "9ea2eab18bc0bf108fffb90245fd7f51a07e0fa16e52d49564e20c50e0718ce3"
EXPECTED_PROVENANCE = {
    "data": "SYNTHETIC price history - not real market data",
    "synthetic": True,
    "seed": 20261117,
    "data_file": (
        "specs/001-portfolio-var-backtest/data/"
        "synthetic_prices_seed20261117.csv"
    ),
    "data_sha256": EXPECTED_SHA256,
    "method": "filtered historical simulation, EWMA λ=0.94",
    "lambda": 0.94,
    "pool_size": 250,
    "warmup": 100,
    "confidence": 0.99,
    "horizon_days": 1,
    "quantile_rule": "linear interpolation, position (n−1)p",
    "as_of_date": "2026-11-13",
}
FIXED_VERDICT_NOTE = (
    "A correct implementation of this method breaches about 1.39% of days "
    "(3.5 per 250), not 1%, because the 1% quantile of a 250-day pool sits "
    "between the 3rd and 4th worst outcomes. Such a model reaches the amber "
    "zone or worse roughly a quarter of the time, so amber alone does not "
    "prove the model wrong. Kupiec is tested against the nominal 1%."
)
PRICED_TICKERS = {
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "NVDA",
    "TSLA",
    "IBM",
    "BAC",
    "C",
    "JPM",
    "GS",
    "MS",
    "UBS",
    "DB",
    "COF",
    "DFS",
    "FNMA",
    "FIS",
    "FNF",
}
SEEDED_POSITIONS = {
    22214: [
        {"security": "C", "quantity": -2000},
        {"security": "IBM", "quantity": -100},
        {"security": "MS", "quantity": 1000},
    ],
    52355: [{"security": "BAC", "quantity": -2400}],
}


def _request(base_url, method, path, body=None):
    encoded_body = None
    headers = {"Accept": "application/json"}
    if body is not None:
        encoded_body = (
            body
            if isinstance(body, bytes)
            else json.dumps(body, allow_nan=False).encode("utf-8")
        )
        headers["Content-Type"] = "application/json"

    request = Request(
        base_url + path,
        data=encoded_body,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=10) as response:
            raw_body = response.read()
            status = response.status
    except HTTPError as error:
        raw_body = error.read()
        status = error.code

    return status, json.loads(raw_body.decode("utf-8"))


def _risk_account(account_id):
    return _request(
        RISK_BASE_URL,
        "GET",
        "/api/v1/risk/accounts/" + quote(str(account_id), safe=""),
    )


def _risk_positions(positions):
    return _request(
        RISK_BASE_URL,
        "POST",
        "/api/v1/risk/positions",
        {"positions": positions},
    )


def _assert_provenance(payload, position_source, positions_read_at):
    provenance = payload["provenance"]

    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["data"] == EXPECTED_PROVENANCE["data"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["synthetic"] is EXPECTED_PROVENANCE["synthetic"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["seed"] == EXPECTED_PROVENANCE["seed"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["data_file"] == EXPECTED_PROVENANCE["data_file"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["data_sha256"] == EXPECTED_PROVENANCE["data_sha256"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["method"] == EXPECTED_PROVENANCE["method"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["lambda"] == EXPECTED_PROVENANCE["lambda"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["pool_size"] == EXPECTED_PROVENANCE["pool_size"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["warmup"] == EXPECTED_PROVENANCE["warmup"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["confidence"] == EXPECTED_PROVENANCE["confidence"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["horizon_days"] == EXPECTED_PROVENANCE["horizon_days"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["quantile_rule"] == EXPECTED_PROVENANCE["quantile_rule"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["as_of_date"] == EXPECTED_PROVENANCE["as_of_date"]
    # spec FR-015 and contracts/data-model.md Provenance.
    assert provenance["position_source"] == position_source
    # contracts/data-model.md Provenance: caller-supplied and unread positions use null.
    assert provenance["positions_read_at"] is positions_read_at

    if positions_read_at:
        # contracts/data-model.md Provenance: TraderX reads use a UTC ISO-8601 timestamp.
        assert isinstance(provenance["positions_read_at"], str)
        datetime.fromisoformat(provenance["positions_read_at"].replace("Z", "+00:00"))


def _assert_no_risk_numbers(payload):
    # contracts/http-api.md Outcome → HTTP status: non-OK results have null risk blocks.
    assert payload.get("current") is None
    # contracts/http-api.md Outcome → HTTP status: non-OK results have null risk blocks.
    assert payload.get("track_record") is None
    # contracts/http-api.md Outcome → HTTP status: non-OK results have null risk blocks.
    assert payload.get("verdict") is None


def _published_history():
    with DATA_FILE.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        tickers = [name for name in reader.fieldnames if name != "date"]
        dates = []
        closes = {ticker: [] for ticker in tickers}
        for row in reader:
            dates.append(row["date"])
            for ticker in tickers:
                closes[ticker].append(float(row[ticker]))
    return dates, closes


def _load_oracle():
    specification = importlib.util.spec_from_file_location(
        "integration_independent_oracle", ORACLE_FILE
    )
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def _strip_updated(value):
    if isinstance(value, dict):
        return {
            key: _strip_updated(child)
            for key, child in value.items()
            if key != "updated"
        }
    if isinstance(value, list):
        return [_strip_updated(child) for child in value]
    return value


def _json_shape(value):
    if isinstance(value, dict):
        return {
            key: _json_shape(child)
            for key, child in sorted(value.items())
        }
    if isinstance(value, list):
        return [_json_shape(child) for child in value]
    return type(value).__name__


def _strings_in_json(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _strings_in_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings_in_json(child)
    elif isinstance(value, str):
        yield value


def _baseline_responses():
    with BASELINE_FILE.open(encoding="utf-8") as source:
        captured = json.load(source)
    return {entry["path"]: entry for entry in captured["responses"]}


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/v1/risk/accounts/not-a-decimal", None),
        (
            "/api/v1/risk/positions",
            [
                {"security": "MS", "quantity": 1},
                {"security": "MS", "quantity": 2},
            ],
        ),
    ],
)
def test_invalid_request_precedes_all_other_outcomes(path, body):
    if body is None:
        status, payload = _request(RISK_BASE_URL, "GET", path)
    else:
        status, payload = _risk_positions(body)

    # contracts/http-api.md Outcome → HTTP status and outcome precedence step 1.
    assert status == 400
    # contracts/http-api.md Outcome → HTTP status and outcome precedence step 1.
    assert payload["outcome"] == "INVALID_REQUEST"
    # spec FR-011 and contracts/data-model.md RiskResult.
    assert isinstance(payload["message"], str)
    _assert_no_risk_numbers(payload)
    _assert_provenance(
        payload,
        "caller-supplied" if body is not None else "TraderX account",
        None,
    )


def test_account_not_found_has_distinct_outcome_and_full_provenance():
    status, payload = _risk_account(99999)

    # spec V6, spec FR-008, and contracts/http-api.md Outcome → HTTP status.
    assert status == 404
    # spec V6, spec FR-008, and contracts/http-api.md Outcome → HTTP status.
    assert payload["outcome"] == "ACCOUNT_NOT_FOUND"
    # contracts/data-model.md RiskResult: account is present only when it was found.
    assert payload.get("account") is None
    _assert_no_risk_numbers(payload)
    _assert_provenance(payload, "TraderX account", None)


def test_zero_quantity_precedes_missing_history_and_returns_no_open_positions():
    status, payload = _risk_positions([{"security": "NOT_PRICED", "quantity": 0}])

    # contracts/http-api.md outcome precedence steps 4 and 5.
    assert status == 200
    # contracts/http-api.md outcome precedence steps 4 and 5.
    assert payload["outcome"] == "NO_OPEN_POSITIONS"
    _assert_no_risk_numbers(payload)
    _assert_provenance(payload, "caller-supplied", None)


def test_no_open_positions_account_has_distinct_outcome_and_full_provenance():
    status, payload = _risk_account(44044)

    # spec V6, spec FR-009, and contracts/http-api.md Outcome → HTTP status.
    assert status == 200
    # spec V6, spec FR-009, and contracts/http-api.md Outcome → HTTP status.
    assert payload["outcome"] == "NO_OPEN_POSITIONS"
    _assert_no_risk_numbers(payload)
    _assert_provenance(payload, "TraderX account", None)


def test_missing_price_history_lists_all_remaining_securities_in_sorted_order():
    status, payload = _risk_positions(
        [
            {"security": "ZZZ", "quantity": 1},
            {"security": "AAA", "quantity": -1},
            {"security": "NOT_PRICED", "quantity": 0},
        ]
    )

    # spec V6, spec FR-010, and contracts/http-api.md Outcome → HTTP status.
    assert status == 422
    # spec V6, spec FR-010, and contracts/http-api.md Outcome → HTTP status.
    assert payload["outcome"] == "MISSING_PRICE_HISTORY"
    # contracts/http-api.md outcome precedence steps 4 and 6.
    assert payload["missing_securities"] == ["AAA", "ZZZ"]
    _assert_no_risk_numbers(payload)
    _assert_provenance(payload, "caller-supplied", None)


@pytest.mark.parametrize("account_id", (22214, 52355))
def test_ok_result_is_fast_complete_and_has_required_track_record(account_id):
    started = time.perf_counter()
    status, payload = _risk_account(account_id)
    elapsed = time.perf_counter() - started

    # spec SC-002: each result for any seeded account appears in under five seconds.
    assert elapsed < 5.0
    # contracts/http-api.md Outcome → HTTP status.
    assert status == 200
    # contracts/http-api.md Outcome → HTTP status.
    assert payload["outcome"] == "OK"
    # contracts/data-model.md RiskResult: account is present for a found account path result.
    assert payload["account"]["id"] == account_id
    _assert_provenance(payload, "TraderX account", True)

    current = payload["current"]
    track_record = payload["track_record"]
    verdict = payload["verdict"]

    # spec FR-001 and contracts/data-model.md CurrentRisk.
    assert isinstance(current["var_usd"], float)
    # spec FR-002 and contracts/data-model.md CurrentRisk.
    assert current["data_as_of"] == "2026-11-13"
    # spec FR-002 and contracts/data-model.md CurrentRisk.
    assert current["forecast_for"] == "2026-11-16"
    # contracts/data-model.md CurrentRisk: positions are sorted by security.
    assert [row["security"] for row in current["positions"]] == sorted(
        row["security"] for row in current["positions"]
    )
    # spec FR-004 and contracts/data-model.md BacktestRow.
    assert len(track_record) == 250
    # spec FR-004 and contracts/data-model.md BacktestRow.
    assert [row["day"] for row in track_record] == list(range(351, 601))
    # spec FR-016 and contracts/http-api.md Fixed verdict note.
    assert verdict["note"] == FIXED_VERDICT_NOTE

    for row in track_record:
        # spec FR-005 and contracts/data-model.md BacktestRow.
        assert row["breach"] is (row["realised_pnl_usd"] < -row["forecast_var_usd"])


def test_caller_supplied_seeded_positions_match_account_result():
    account_status, account_result = _risk_account(22214)
    supplied_status, supplied_result = _risk_positions(SEEDED_POSITIONS[22214])

    # contracts/http-api.md Outcome → HTTP status.
    assert account_status == 200
    # contracts/http-api.md Outcome → HTTP status.
    assert supplied_status == 200
    # spec V6 and spec FR-020.
    assert account_result["outcome"] == "OK"
    # spec V6 and spec FR-020.
    assert supplied_result["outcome"] == "OK"
    # spec V6 and spec FR-020: the same positions give the same current VaR.
    assert supplied_result["current"] == account_result["current"]
    # spec V6 and spec FR-020: the same positions give the same track record.
    assert supplied_result["track_record"] == account_result["track_record"]
    # spec V6 and spec FR-020: the same positions give the same verdict.
    assert supplied_result["verdict"] == account_result["verdict"]
    # contracts/http-api.md Caller-supplied body rules.
    assert "account" not in supplied_result
    _assert_provenance(account_result, "TraderX account", True)
    _assert_provenance(supplied_result, "caller-supplied", None)


@pytest.mark.parametrize("account_id", (22214, 52355))
def test_http_results_agree_with_independent_oracle(account_id):
    oracle = _load_oracle()
    dates, closes = _published_history()
    positions = {
        item["security"]: float(item["quantity"])
        for item in SEEDED_POSITIONS[account_id]
    }
    oracle_backtest = oracle.backtest(
        oracle.pnl_series(closes, positions), oracle.Params()
    )
    status, payload = _risk_account(account_id)

    # contracts/http-api.md Outcome → HTTP status.
    assert status == 200
    # spec V3 and SC-004: the seeded account result is available for comparison.
    assert payload["outcome"] == "OK"
    # spec V3 and SC-004: current VaR agrees within $0.01.
    assert abs(payload["current"]["var_usd"] - oracle_backtest.current_var) <= 0.01
    # spec FR-004 and V3: 250 backtest account-days are compared.
    assert len(payload["track_record"]) == 250

    for expected_day, expected_date, row, oracle_row in zip(
        range(351, 601),
        dates[351:601],
        payload["track_record"],
        oracle_backtest.rows,
    ):
        # contracts/data-model.md BacktestRow.
        assert row["day"] == expected_day
        # contracts/data-model.md BacktestRow.
        assert row["date"] == expected_date
        # spec V3 and SC-004: every backtest forecast agrees within $0.01.
        assert abs(row["forecast_var_usd"] - oracle_row.forecast_var) <= 0.01
        # spec V3 and SC-004: breach flags are identical on all account-days.
        assert row["breach"] is oracle_row.breach

    breaches = sum(row.breach for row in oracle_backtest.rows)
    expected_kupiec = oracle.kupiec(breaches, T=250, p=0.01)
    verdict = payload["verdict"]

    # spec V3: verdict breach counts are identical.
    assert verdict["breaches"] == breaches
    # spec V3: verdict rejection decisions are identical.
    assert verdict["kupiec"]["reject_5pct"] is expected_kupiec.reject
    # spec V3: verdict rejection directions are identical.
    assert verdict["kupiec"]["direction"] == expected_kupiec.direction
    # spec V3: Basel verdict fields are identical.
    assert verdict["basel_zone"] == oracle.basel_zone(breaches)
    # spec V3: Kupiec LR agrees within 1e-6.
    assert abs(verdict["kupiec"]["lr"] - expected_kupiec.lr) <= 1e-6
    # spec V3: Kupiec p-value agrees within 1e-6.
    assert abs(verdict["kupiec"]["p_value"] - expected_kupiec.p_value) <= 1e-6


def test_repeated_requests_have_identical_numeric_result_blocks():
    first_status, first = _risk_positions(SEEDED_POSITIONS[22214])
    second_status, second = _risk_positions(SEEDED_POSITIONS[22214])

    # contracts/http-api.md Outcome → HTTP status.
    assert first_status == 200
    # contracts/http-api.md Outcome → HTTP status.
    assert second_status == 200

    for block in ("current", "track_record", "verdict"):
        first_numeric_bytes = json.dumps(
            first[block], sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        second_numeric_bytes = json.dumps(
            second[block], sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")

        # spec SC-008 and amendment M3: these blocks are byte-identical across runs.
        assert first_numeric_bytes == second_numeric_bytes


def test_traderx_baseline_responses_are_preserved_under_sc007_rules():
    baseline = _baseline_responses()
    account_and_position_paths = (
        "/account-service/account/22214",
        "/account-service/account/52355",
        "/position-service/positions/22214",
        "/position-service/positions/52355",
    )

    for path in account_and_position_paths:
        # contracts/test-harness.md Baseline responses: these paths are captured.
        assert path in baseline

        after_status, after_body = _request(TRADERX_BASE_URL, "GET", path)
        before = baseline[path]

        # spec SC-007: seeded account and position lookup status is unchanged.
        assert after_status == before["status"]
        # spec SC-007: seeded account and position responses match ignoring updated.
        assert _strip_updated(after_body) == _strip_updated(before["body"])

    price_path = "/price-publisher/prices"

    # contracts/test-harness.md Baseline responses: the price path is captured.
    assert price_path in baseline

    after_status, after_body = _request(TRADERX_BASE_URL, "GET", price_path)
    before = baseline[price_path]["body"]
    before_tickers = set(_strings_in_json(before)) & PRICED_TICKERS
    after_tickers = set(_strings_in_json(after_body)) & PRICED_TICKERS

    # spec SC-007: the price lookup status remains unchanged.
    assert after_status == baseline[price_path]["status"]
    # spec SC-007: the price lookup preserves the set of tickers.
    assert after_tickers == before_tickers
    # spec SC-007: the price lookup preserves its response shape while values may move.
    assert _json_shape(after_body) == _json_shape(before)
```

Open questions

The contracts provide no request or test-harness mechanism to induce `POSITIONS_UNAVAILABLE` or `ZERO_VOLATILITY` against the fixed running stack. Consequently, those two HTTP outcomes cannot be independently exercised without an agreed dependency-failure fixture or configurable synthetic-history input.