```python file=tests/integration/conftest.py
import os

import pytest


@pytest.fixture(scope="session")
def risk_base_url():
    return os.environ.get("RISK_BASE_URL", "http://127.0.0.1:18110").rstrip("/")


@pytest.fixture(scope="session")
def traderx_base_url():
    return os.environ.get("TRADERX_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
```

```python file=tests/integration/test_integration_http_contract.py
import csv
import importlib.util
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPOSITORY_ROOT / "specs/001-portfolio-var-backtest/data"
BASELINE_PATH = (
    REPOSITORY_ROOT
    / "specs/001-portfolio-var-backtest/validation/runs/baseline-before.json"
)

DATA_SHA256 = "9ea2eab18bc0bf108fffb90245fd7f51a07e0fa16e52d49564e20c50e0718ce3"
DATA_FILE = (
    "specs/001-portfolio-var-backtest/data/"
    "synthetic_prices_seed20261117.csv"
)
PROVENANCE_CONSTANTS = {
    "data": "SYNTHETIC price history - not real market data",
    "synthetic": True,
    "seed": 20261117,
    "data_file": DATA_FILE,
    "data_sha256": DATA_SHA256,
    "method": "filtered historical simulation, EWMA λ=0.94",
    "lambda": 0.94,
    "pool_size": 250,
    "warmup": 100,
    "confidence": 0.99,
    "horizon_days": 1,
    "quantile_rule": "linear interpolation, position (n−1)p",
    "as_of_date": "2026-11-13",
}
SEEDED_POSITIONS = {
    22214: {"C": -2000.0, "IBM": -100.0, "MS": 1000.0},
    52355: {"BAC": -2400.0},
}


def _request(base_url, method, path, body=None):
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"

    request = Request(
        base_url + path,
        data=body,
        headers=headers,
        method=method,
    )
    started = time.monotonic()
    try:
        with urlopen(request, timeout=10) as response:
            status = response.status
            payload = response.read()
    except HTTPError as error:
        status = error.code
        payload = error.read()
    elapsed = time.monotonic() - started
    return status, json.loads(payload.decode("utf-8")), elapsed


def _post_positions(base_url, positions):
    return _request(
        base_url,
        "POST",
        "/api/v1/risk/positions",
        json.dumps({"positions": positions}).encode("utf-8"),
    )


def _is_utc_iso8601(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(
        parsed
    )


def _assert_provenance(result, expected_source=None, positions_read_at=None):
    # spec FR-015 and SC-006: every response carries full provenance.
    assert "provenance" in result
    provenance = result["provenance"]

    for field, expected in PROVENANCE_CONSTANTS.items():
        # contracts/data-model.md Provenance: each fixed provenance field has its specified value.
        assert provenance.get(field) == expected

    if expected_source is None:
        # contracts/data-model.md Provenance: position_source is one of the two documented sources.
        assert provenance.get("position_source") in {
            "TraderX account",
            "caller-supplied",
        }
    else:
        # contracts/data-model.md Provenance: the response identifies the documented position source.
        assert provenance.get("position_source") == expected_source

    if positions_read_at == "timestamp":
        # contracts/data-model.md Provenance: successful TraderX position reads use a UTC ISO-8601 timestamp.
        assert _is_utc_iso8601(provenance.get("positions_read_at"))
    else:
        # contracts/data-model.md Provenance: caller input and pre-position-read outcomes have a null read time.
        assert provenance.get("positions_read_at") is None


def _assert_outcome(status, result, expected_status, expected_outcome):
    # contracts/http-api.md Outcome → HTTP status: each outcome has its documented status.
    assert status == expected_status
    # contracts/data-model.md RiskResult: outcome is always present and machine-readable.
    assert result.get("outcome") == expected_outcome
    # contracts/data-model.md RiskResult: message is always present and human-readable.
    assert isinstance(result.get("message"), str) and result["message"].strip()


def _assert_no_risk_blocks(result):
    for field in ("current", "track_record", "verdict"):
        if field in result:
            # contracts/http-api.md Outcome → HTTP status: non-OK outcomes have null risk blocks.
            assert result[field] is None


def _assert_ok_result(result):
    for field in ("current", "track_record", "verdict"):
        # contracts/http-api.md Outcome → HTTP status: OK responses include every risk block.
        assert result.get(field) is not None


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _remove_updated(value):
    if isinstance(value, dict):
        return {
            key: _remove_updated(item)
            for key, item in value.items()
            if key != "updated"
        }
    if isinstance(value, list):
        return [_remove_updated(item) for item in value]
    return value


def _json_shape(value):
    if isinstance(value, dict):
        return {key: _json_shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_shape(item) for item in value]
    return type(value).__name__


def _string_leaves(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _string_leaves(item)
    elif isinstance(value, list):
        for item in value:
            yield from _string_leaves(item)
    elif isinstance(value, str):
        yield value


def _published_closes():
    configured = Path(os.environ.get("RISK_DATA_DIR", str(DEFAULT_DATA_DIR)))
    data_dir = configured if configured.is_absolute() else REPOSITORY_ROOT / configured
    data_path = data_dir / "synthetic_prices_seed20261117.csv"

    with data_path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        tickers = [field for field in reader.fieldnames if field != "date"]
        closes = {ticker: [] for ticker in tickers}
        for row in reader:
            for ticker in tickers:
                closes[ticker].append(float(row[ticker]))
    return tickers, closes


def _load_oracle_module():
    module_path = REPOSITORY_ROOT / "tests/oracle/oracle_independent_var.py"
    spec = importlib.util.spec_from_file_location(
        "integration_independent_var_oracle", module_path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_v6_outcomes_and_provenance(risk_base_url):
    status, unknown, _ = _request(
        risk_base_url, "GET", "/api/v1/risk/accounts/99999"
    )
    _assert_outcome(status, unknown, 404, "ACCOUNT_NOT_FOUND")
    _assert_no_risk_blocks(unknown)
    _assert_provenance(
        unknown,
        expected_source="TraderX account",
        positions_read_at=None,
    )

    status, empty_account, _ = _request(
        risk_base_url, "GET", "/api/v1/risk/accounts/44044"
    )
    _assert_outcome(status, empty_account, 200, "NO_OPEN_POSITIONS")
    _assert_no_risk_blocks(empty_account)
    _assert_provenance(
        empty_account,
        expected_source="TraderX account",
        positions_read_at="timestamp",
    )

    status, missing_history, _ = _post_positions(
        risk_base_url,
        [
            {"security": "ZZZ", "quantity": 1},
            {"security": "AAA", "quantity": -2},
        ],
    )
    _assert_outcome(status, missing_history, 422, "MISSING_PRICE_HISTORY")
    _assert_no_risk_blocks(missing_history)
    _assert_provenance(
        missing_history,
        expected_source="caller-supplied",
        positions_read_at=None,
    )
    # contracts/http-api.md Outcome precedence step 6: every missing security is listed sorted.
    assert missing_history.get("missing_securities") == ["AAA", "ZZZ"]


def test_caller_positions_match_account_22214_and_have_caller_provenance(risk_base_url):
    status, account_result, _ = _request(
        risk_base_url, "GET", "/api/v1/risk/accounts/22214"
    )
    _assert_outcome(status, account_result, 200, "OK")
    _assert_ok_result(account_result)
    _assert_provenance(
        account_result,
        expected_source="TraderX account",
        positions_read_at="timestamp",
    )

    caller_positions = [
        {"security": "C", "quantity": -2000},
        {"security": "IBM", "quantity": -100},
        {"security": "MS", "quantity": 1000},
    ]
    status, caller_result, _ = _post_positions(risk_base_url, caller_positions)
    _assert_outcome(status, caller_result, 200, "OK")
    _assert_ok_result(caller_result)
    _assert_provenance(
        caller_result,
        expected_source="caller-supplied",
        positions_read_at=None,
    )

    for field in ("current", "track_record", "verdict"):
        # spec V6 and FR-020: identical caller positions produce the same risk results as account 22214.
        assert caller_result[field] == account_result[field]
    # contracts/http-api.md Caller-supplied body rules: account is absent for caller-supplied positions.
    assert "account" not in caller_result


def test_outcome_precedence_for_invalid_and_zero_quantity_positions(risk_base_url):
    status, invalid_account, _ = _request(
        risk_base_url, "GET", "/api/v1/risk/accounts/not-a-decimal-id"
    )
    _assert_outcome(status, invalid_account, 400, "INVALID_REQUEST")
    _assert_no_risk_blocks(invalid_account)
    _assert_provenance(invalid_account, positions_read_at=None)

    invalid_bodies = (
        b'{"positions":"not-a-list"}',
        b'{"positions":[{"security":"","quantity":1}]}',
        b'{"positions":[{"security":"MS","quantity":1},{"security":"MS","quantity":2}]}',
        b'{"positions":[{"security":"MS","quantity":1e999}]}',
        b'{"positions":[{"security":"UNPRICED","quantity":0},{"security":"UNPRICED","quantity":0}]}',
    )
    for body in invalid_bodies:
        status, invalid_result, _ = _request(
            risk_base_url,
            "POST",
            "/api/v1/risk/positions",
            body,
        )
        _assert_outcome(status, invalid_result, 400, "INVALID_REQUEST")
        _assert_no_risk_blocks(invalid_result)
        _assert_provenance(invalid_result, positions_read_at=None)

    status, zero_unpriced, _ = _post_positions(
        risk_base_url,
        [{"security": "UNPRICED", "quantity": 0}],
    )
    _assert_outcome(status, zero_unpriced, 200, "NO_OPEN_POSITIONS")
    _assert_no_risk_blocks(zero_unpriced)
    _assert_provenance(
        zero_unpriced,
        expected_source="caller-supplied",
        positions_read_at=None,
    )
    # contracts/http-api.md Outcome precedence steps 4–5: zero quantity is dropped before missing-history checks.
    assert "missing_securities" not in zero_unpriced or (
        zero_unpriced["missing_securities"] is None
    )


def test_response_time_for_each_seeded_account(risk_base_url):
    for account_id in SEEDED_POSITIONS:
        status, result, elapsed = _request(
            risk_base_url,
            "GET",
            "/api/v1/risk/accounts/{}".format(account_id),
        )
        _assert_outcome(status, result, 200, "OK")
        _assert_ok_result(result)
        _assert_provenance(
            result,
            expected_source="TraderX account",
            positions_read_at="timestamp",
        )
        # spec SC-002: current VaR, track record, and verdict appear in under five seconds.
        assert elapsed < 5.0


def test_http_results_agree_with_independent_oracle(risk_base_url):
    oracle = _load_oracle_module()
    _, closes = _published_closes()

    for account_id, positions in SEEDED_POSITIONS.items():
        status, result, _ = _request(
            risk_base_url,
            "GET",
            "/api/v1/risk/accounts/{}".format(account_id),
        )
        _assert_outcome(status, result, 200, "OK")
        _assert_ok_result(result)

        actual_positions = {
            item["security"]: float(item["quantity"])
            for item in result["current"]["positions"]
        }
        # spec V3: the comparison uses the documented seeded account positions.
        assert actual_positions == positions

        oracle_pnl = oracle.pnl_series(closes, positions)
        oracle_backtest = oracle.backtest(oracle_pnl, oracle.Params())

        # spec V3 and SC-004: current VaR agrees with the independent implementation within $0.01.
        assert (
            abs(result["current"]["var_usd"] - oracle_backtest.current_var) <= 0.01
        )
        # spec FR-004 and V3: each seeded account supplies exactly 250 compared backtest days.
        assert len(result["track_record"]) == 250

        for expected_day, http_row, oracle_row in zip(
            range(351, 601),
            result["track_record"],
            oracle_backtest.rows,
        ):
            # contracts/data-model.md BacktestRow: rows are ordered by day 351 through 600.
            assert http_row["day"] == expected_day
            # spec V3 and SC-004: every backtest forecast agrees within $0.01.
            assert abs(http_row["forecast_var_usd"] - oracle_row.forecast_var) <= 0.01
            # spec V3 and SC-004: every breach flag matches the independent implementation.
            assert http_row["breach"] is oracle_row.breach

        oracle_breaches = sum(row.breach for row in oracle_backtest.rows)
        oracle_kupiec = oracle.kupiec(oracle_breaches, T=250, p=0.01)
        verdict = result["verdict"]

        # spec V3: breach counts in the verdict are identical.
        assert verdict["breaches"] == oracle_breaches
        # spec V3: the verdict breach rate is identical.
        assert verdict["breach_rate"] == oracle_breaches / 250
        # spec V3: Kupiec LR agrees within 1e-6.
        assert abs(verdict["kupiec"]["lr"] - oracle_kupiec.lr) <= 1e-6
        # spec V3: Kupiec p-value agrees within 1e-6.
        assert abs(verdict["kupiec"]["p_value"] - oracle_kupiec.p_value) <= 1e-6
        # spec V3: Kupiec rejection decisions are identical.
        assert verdict["kupiec"]["reject_5pct"] is oracle_kupiec.reject
        # spec V3: Kupiec rejection directions are identical.
        assert verdict["kupiec"]["direction"] == oracle_kupiec.direction
        # spec V3: Basel verdict fields are identical.
        assert verdict["basel_zone"] == oracle.basel_zone(oracle_breaches)
        # spec M7 and V3: the finite-sample rate agrees with the independent implementation.
        assert math.isclose(
            verdict["finite_sample_rate"],
            oracle.finite_sample_rate(250, 0.01),
            rel_tol=0.0,
            abs_tol=1e-9,
        )


def test_numeric_result_blocks_are_deterministic(risk_base_url):
    status, first, _ = _request(
        risk_base_url, "GET", "/api/v1/risk/accounts/22214"
    )
    _assert_outcome(status, first, 200, "OK")
    status, second, _ = _request(
        risk_base_url, "GET", "/api/v1/risk/accounts/22214"
    )
    _assert_outcome(status, second, 200, "OK")

    for field in ("current", "track_record", "verdict"):
        # spec SC-008: numeric result blocks are byte-identical for the same positions.
        assert _canonical_json(first[field]) == _canonical_json(second[field])


def test_baseline_traderx_responses_are_preserved(traderx_base_url):
    # contracts/test-harness.md Baseline responses: the captured baseline file is the comparison input.
    assert BASELINE_PATH.exists()
    with BASELINE_PATH.open(encoding="utf-8") as source:
        baseline = json.load(source)

    # contracts/test-harness.md Baseline responses: captures are stored as a responses list.
    assert isinstance(baseline.get("responses"), list)

    ticker_names, _ = _published_closes()
    expected_tickers = set(ticker_names)

    for captured in baseline["responses"]:
        path = captured["path"]
        status, after_body, _ = _request(traderx_base_url, "GET", path)

        # spec SC-007: each preserved TraderX endpoint keeps its baseline HTTP status.
        assert status == captured["status"]

        if path == "/price-publisher/prices":
            # spec SC-007: the price lookup retains the same response shape.
            assert _json_shape(after_body) == _json_shape(captured["body"])
            baseline_tickers = {
                value
                for value in _string_leaves(captured["body"])
                if value in expected_tickers
            }
            after_tickers = {
                value
                for value in _string_leaves(after_body)
                if value in expected_tickers
            }
            # spec SC-007: the baseline price lookup exposes the frozen ticker set.
            assert baseline_tickers == expected_tickers
            # spec SC-007: the post-feature price lookup exposes the same ticker set.
            assert after_tickers == expected_tickers
        else:
            # spec SC-007: account and position lookups are unchanged except for updated.
            assert _remove_updated(after_body) == _remove_updated(captured["body"])
```

Open questions

- The HTTP contract provides no documented way to induce `POSITIONS_UNAVAILABLE` in the running stack, or to create a non-empty zero-volatility portfolio from the frozen history. Those two outcome/status combinations therefore cannot be exercised without an additional test-only dependency-control mechanism.
- SC-008 requires comparison across clean starts, while the tier-2 harness exposes only already-running base URLs. The determinism test compares two requests to the supplied running stack.