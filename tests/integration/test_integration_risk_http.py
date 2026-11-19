import csv
import importlib.util
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RISK_BASE_URL = os.environ.get("RISK_BASE_URL", "http://127.0.0.1:18110").rstrip("/")
TRADERX_BASE_URL = os.environ.get(
    "TRADERX_BASE_URL", "http://127.0.0.1:8080"
).rstrip("/")
DEFAULT_DATA_DIR = REPOSITORY_ROOT / "specs/001-portfolio-var-backtest/data"
DATA_DIR = Path(os.environ.get("RISK_DATA_DIR", str(DEFAULT_DATA_DIR)))
if not DATA_DIR.is_absolute():
    DATA_DIR = REPOSITORY_ROOT / DATA_DIR

BASELINE_PATH = (
    REPOSITORY_ROOT
    / "specs/001-portfolio-var-backtest/validation/runs/baseline-before.json"
)
ORACLE_PATH = REPOSITORY_ROOT / "tests/oracle/oracle_independent_var.py"

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

SEEDED_ACCOUNTS = (
    (22214, {"C": -2000.0, "IBM": -100.0, "MS": 1000.0}),
    (52355, {"BAC": -2400.0}),
)

FIXED_VERDICT_NOTE = (
    "A correct implementation of this method breaches about 1.39% of days "
    "(3.5 per 250), not 1%, because the 1% quantile of a 250-day pool sits "
    "between the 3rd and 4th worst outcomes. Such a model reaches the amber "
    "zone or worse roughly a quarter of the time, so amber alone does not "
    "prove the model wrong. Kupiec is tested against the nominal 1%."
)


def _load_oracle():
    module_name = "_integration_oracle_independent_var"
    spec = importlib.util.spec_from_file_location(module_name, ORACLE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


ORACLE = _load_oracle()


def _decode_body(raw_body):
    text = raw_body.decode("utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _request(base_url, method, path, payload=None, timeout=10):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, allow_nan=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        base_url + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, _decode_body(response.read())
    except urllib.error.HTTPError as response:
        return response.code, _decode_body(response.read())


def _risk_json(method, path, payload=None, timeout=10):
    status, response = _request(
        RISK_BASE_URL, method, path, payload=payload, timeout=timeout
    )
    # contracts/http-api.md Responses: risk-service responses are JSON.
    assert isinstance(response, dict)
    return status, response


def _published_history():
    path = DATA_DIR / "synthetic_prices_seed20261117.csv"
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        tickers = [name for name in reader.fieldnames if name != "date"]
        closes = {ticker: [] for ticker in tickers}
        dates = []
        for row in reader:
            dates.append(row["date"])
            for ticker in tickers:
                closes[ticker].append(float(row[ticker]))
    return dates, closes


def _assert_provenance(response, position_source, positions_read_at):
    provenance = response["provenance"]

    # data-model.md Provenance: every result names the synthetic data label.
    assert provenance["data"] == "SYNTHETIC price history - not real market data"
    # spec FR-015: every result, errors included, carries synthetic provenance.
    assert provenance["synthetic"] is True
    # spec M1 and FR-015: the frozen-history seed is 20261117.
    assert provenance["seed"] == 20261117
    # contracts/http-api.md RiskResult example: provenance identifies the data file.
    assert (
        provenance["data_file"]
        == "specs/001-portfolio-var-backtest/data/"
        "synthetic_prices_seed20261117.csv"
    )
    # spec M1 and FR-014: the published CSV checksum is fixed.
    assert (
        provenance["data_sha256"]
        == "9ea2eab18bc0bf108fffb90245fd7f51a07e0fa16e52d49564e20c50e0718ce3"
    )
    # spec FR-015: provenance records the required method name.
    assert provenance["method"] == "filtered historical simulation, EWMA λ=0.94"
    # spec M3: lambda is 0.94.
    assert provenance["lambda"] == 0.94
    # spec M4 and M5: the residual pool contains 250 observations.
    assert provenance["pool_size"] == 250
    # spec M3: the EWMA warm-up is 100 days.
    assert provenance["warmup"] == 100
    # spec M5 and FR-015: confidence is 99%.
    assert provenance["confidence"] == 0.99
    # spec FR-001 and FR-015: the forecast horizon is one day.
    assert provenance["horizon_days"] == 1
    # spec M4 and FR-015: this exact quantile convention is required.
    assert provenance["quantile_rule"] == "linear interpolation, position (n−1)p"
    # spec M1 and FR-015: the fixed as-of date is 2026-11-13.
    assert provenance["as_of_date"] == "2026-11-13"
    # spec FR-015 and FR-020: provenance identifies how positions were supplied.
    assert provenance["position_source"] == position_source

    if positions_read_at:
        # data-model.md Provenance: successful account reads use a UTC ISO-8601 timestamp.
        assert isinstance(provenance["positions_read_at"], str)
        # data-model.md Provenance: TraderX read timestamps are UTC.
        assert provenance["positions_read_at"].endswith("Z")
        parsed = datetime.fromisoformat(
            provenance["positions_read_at"][:-1] + "+00:00"
        )
        # data-model.md Provenance: the timestamp is explicitly UTC.
        assert parsed.tzinfo == timezone.utc
    else:
        # data-model.md Provenance: caller input and pre-lookup errors have no read timestamp.
        assert provenance["positions_read_at"] is None


def _assert_no_risk_blocks(response):
    for field in ("current", "track_record", "verdict"):
        # data-model.md RiskResult: non-OK outcomes omit these blocks or set them to null.
        assert field not in response or response[field] is None


def _minimum_subnormal_zero_volatility_positions():
    _, closes = _published_history()
    quantity = float.fromhex("0x0.0000000000001p-1022")

    # contracts/http-api.md caller positions accept any non-zero finite JSON number.
    assert quantity > 0.0
    for ticker in sorted(closes):
        warmup_pnl = [
            quantity * (closes[ticker][day] - closes[ticker][day - 1])
            for day in range(1, 101)
        ]
        if all(value == 0.0 for value in warmup_pnl):
            return {"positions": [{"security": ticker, "quantity": quantity}]}

    # spec M3: this frozen history must permit a constructed all-zero warm-up P&L input.
    assert False, "no finite caller-supplied subnormal quantity produced zero warm-up P&L"


def _without_updated(value):
    if isinstance(value, dict):
        return {
            key: _without_updated(item)
            for key, item in value.items()
            if key != "updated"
        }
    if isinstance(value, list):
        return [_without_updated(item) for item in value]
    return value


def _shape(value):
    if isinstance(value, dict):
        return (
            "object",
            tuple(sorted((key, _shape(item)) for key, item in value.items())),
        )
    if isinstance(value, list):
        return ("array", tuple(_shape(item) for item in value))
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


def _priced_tickers_in(value):
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in PRICED_TICKERS:
                found.add(key)
            found.update(_priced_tickers_in(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_priced_tickers_in(item))
    elif isinstance(value, str) and value in PRICED_TICKERS:
        found.add(value)
    return found


def test_outcomes_precedence_and_provenance():
    outcomes = []

    status, unknown = _risk_json("GET", "/api/v1/risk/accounts/99999")
    # contracts/http-api.md Outcome → HTTP status: ACCOUNT_NOT_FOUND is 404.
    assert status == 404
    # spec V6 and FR-008: account 99999 has the distinct not-found outcome.
    assert unknown["outcome"] == "ACCOUNT_NOT_FOUND"
    # data-model.md RiskResult: account lookup errors are human-readable.
    assert isinstance(unknown["message"], str) and unknown["message"]
    _assert_no_risk_blocks(unknown)
    _assert_provenance(unknown, "TraderX account", positions_read_at=False)
    outcomes.append((unknown["outcome"], unknown["message"]))

    status, no_positions = _risk_json("GET", "/api/v1/risk/accounts/44044")
    # contracts/http-api.md Outcome → HTTP status: NO_OPEN_POSITIONS is 200.
    assert status == 200
    # spec V6 and FR-009: account 44044 has no open positions.
    assert no_positions["outcome"] == "NO_OPEN_POSITIONS"
    # data-model.md RiskResult: every outcome supplies a human-readable message.
    assert isinstance(no_positions["message"], str) and no_positions["message"]
    _assert_no_risk_blocks(no_positions)
    _assert_provenance(no_positions, "TraderX account", positions_read_at=True)
    outcomes.append((no_positions["outcome"], no_positions["message"]))

    status, missing = _risk_json(
        "POST",
        "/api/v1/risk/positions",
        {
            "positions": [
                {"security": "NO_HISTORY_Z", "quantity": 1},
                {"security": "NO_HISTORY_A", "quantity": -1},
            ]
        },
    )
    # contracts/http-api.md Outcome → HTTP status: MISSING_PRICE_HISTORY is 422.
    assert status == 422
    # spec V6 and FR-010: unpriced caller securities have a distinct missing-history outcome.
    assert missing["outcome"] == "MISSING_PRICE_HISTORY"
    # contracts/http-api.md Outcome precedence step 6: every missing security is sorted.
    assert missing["missing_securities"] == ["NO_HISTORY_A", "NO_HISTORY_Z"]
    # data-model.md RiskResult: every outcome supplies a human-readable message.
    assert isinstance(missing["message"], str) and missing["message"]
    _assert_no_risk_blocks(missing)
    _assert_provenance(missing, "caller-supplied", positions_read_at=False)
    outcomes.append((missing["outcome"], missing["message"]))

    status, zero_volatility = _risk_json(
        "POST",
        "/api/v1/risk/positions",
        _minimum_subnormal_zero_volatility_positions(),
    )
    # contracts/http-api.md Outcome → HTTP status: ZERO_VOLATILITY is 422.
    assert status == 422
    # contracts/http-api.md Outcome precedence step 7: all-zero warm-up P&L is ZERO_VOLATILITY.
    assert zero_volatility["outcome"] == "ZERO_VOLATILITY"
    # data-model.md RiskResult: every outcome supplies a human-readable message.
    assert isinstance(zero_volatility["message"], str) and zero_volatility["message"]
    _assert_no_risk_blocks(zero_volatility)
    _assert_provenance(zero_volatility, "caller-supplied", positions_read_at=False)
    outcomes.append((zero_volatility["outcome"], zero_volatility["message"]))

    status, invalid_account = _risk_json(
        "GET", "/api/v1/risk/accounts/not-a-decimal-account-id"
    )
    # contracts/http-api.md Outcome → HTTP status: INVALID_REQUEST is 400.
    assert status == 400
    # contracts/http-api.md accountId rule: a non-decimal account ID is INVALID_REQUEST.
    assert invalid_account["outcome"] == "INVALID_REQUEST"
    # data-model.md RiskResult: every outcome supplies a human-readable message.
    assert isinstance(invalid_account["message"], str) and invalid_account["message"]
    _assert_no_risk_blocks(invalid_account)
    _assert_provenance(invalid_account, "TraderX account", positions_read_at=False)
    outcomes.append((invalid_account["outcome"], invalid_account["message"]))

    status, duplicate_before_missing = _risk_json(
        "POST",
        "/api/v1/risk/positions",
        {
            "positions": [
                {"security": "NO_HISTORY_A", "quantity": 1},
                {"security": "NO_HISTORY_A", "quantity": 2},
            ]
        },
    )
    # contracts/http-api.md Outcome → HTTP status: INVALID_REQUEST is 400.
    assert status == 400
    # contracts/http-api.md Outcome precedence step 1: duplicate securities win over missing history.
    assert duplicate_before_missing["outcome"] == "INVALID_REQUEST"
    _assert_no_risk_blocks(duplicate_before_missing)
    _assert_provenance(
        duplicate_before_missing, "caller-supplied", positions_read_at=False
    )

    status, zero_quantity_before_missing = _risk_json(
        "POST",
        "/api/v1/risk/positions",
        {"positions": [{"security": "NO_HISTORY_A", "quantity": 0}]},
    )
    # contracts/http-api.md Outcome → HTTP status: NO_OPEN_POSITIONS is 200.
    assert status == 200
    # contracts/http-api.md Outcome precedence steps 4-5: zero quantities are dropped before history checks.
    assert zero_quantity_before_missing["outcome"] == "NO_OPEN_POSITIONS"
    _assert_no_risk_blocks(zero_quantity_before_missing)
    _assert_provenance(
        zero_quantity_before_missing, "caller-supplied", positions_read_at=False
    )

    # FR-011: outcomes are distinguishable by machine-readable outcome code.
    assert len({outcome for outcome, _ in outcomes}) == len(outcomes)
    # FR-011: outcomes are distinguishable to a person by their response messages.
    assert len({message for _, message in outcomes}) == len(outcomes)


def test_caller_positions_match_account_22214_and_mark_provenance():
    status, account_result = _risk_json("GET", "/api/v1/risk/accounts/22214")
    # contracts/http-api.md Outcome → HTTP status: OK is 200.
    assert status == 200
    # spec V6: seeded account 22214 is a successful risk result.
    assert account_result["outcome"] == "OK"
    _assert_provenance(account_result, "TraderX account", positions_read_at=True)

    status, caller_result = _risk_json(
        "POST",
        "/api/v1/risk/positions",
        {
            "positions": [
                {"security": "MS", "quantity": 1000},
                {"security": "IBM", "quantity": -100},
                {"security": "C", "quantity": -2000},
            ]
        },
    )
    # contracts/http-api.md Outcome → HTTP status: OK is 200.
    assert status == 200
    # spec V6 and FR-020: caller-supplied seeded positions produce an OK result.
    assert caller_result["outcome"] == "OK"
    _assert_provenance(caller_result, "caller-supplied", positions_read_at=False)

    # contracts/http-api.md Caller-supplied body rules: caller results have no account object.
    assert "account" not in caller_result
    for block in ("current", "track_record", "verdict"):
        # spec V6 and FR-020: caller positions return the same risk result blocks as account 22214.
        assert caller_result[block] == account_result[block]


def test_http_results_match_the_independent_oracle():
    dates, closes = _published_history()

    for account_id, positions in SEEDED_ACCOUNTS:
        status, result = _risk_json(
            "GET", "/api/v1/risk/accounts/{}".format(account_id)
        )
        # contracts/http-api.md Outcome → HTTP status: OK is 200.
        assert status == 200
        # spec V3: both seeded accounts have computed results for oracle comparison.
        assert result["outcome"] == "OK"

        oracle_pnl = ORACLE.pnl_series(closes, positions)
        oracle_backtest = ORACLE.backtest(oracle_pnl, ORACLE.Params())

        # spec V3 and SC-004: each current VaR agrees with the independent implementation within $0.01.
        assert (
            abs(result["current"]["var_usd"] - oracle_backtest.current_var) <= 0.01
        )
        # spec FR-002: the result labels the frozen data's as-of date.
        assert result["current"]["data_as_of"] == "2026-11-13"
        # spec FR-002: the next synthetic business day is the forecast date.
        assert result["current"]["forecast_for"] == "2026-11-16"
        # spec FR-004: the HTTP backtest has exactly 250 rows.
        assert len(result["track_record"]) == 250
        # data-model.md BacktestRow: rows are ordered by t = 351 through 600.
        assert [row["day"] for row in result["track_record"]] == list(range(351, 601))
        # data-model.md BacktestRow: each row date is the synthetic date indexed by t.
        assert [row["date"] for row in result["track_record"]] == dates[351:601]

        for http_row, oracle_row in zip(
            result["track_record"], oracle_backtest.rows
        ):
            # spec V3 and SC-004: every backtest forecast agrees within $0.01.
            assert (
                abs(http_row["forecast_var_usd"] - oracle_row.forecast_var) <= 0.01
            )
            # spec V3 and SC-004: all 500 seeded-account breach flags are identical.
            assert http_row["breach"] is oracle_row.breach

        breaches = sum(row.breach for row in oracle_backtest.rows)
        oracle_kupiec = ORACLE.kupiec(breaches, T=250, p=0.01)
        verdict = result["verdict"]

        # spec FR-006: a verdict covers 250 observations.
        assert verdict["observations"] == 250
        # spec V3: verdict breach counts are identical.
        assert verdict["breaches"] == breaches
        # spec FR-006: breach rate is the count divided by 250.
        assert verdict["breach_rate"] == breaches / 250
        # spec M7 and data-model.md Verdict: finite-sample rate agrees within 1e-9.
        assert (
            abs(
                verdict["finite_sample_rate"]
                - ORACLE.finite_sample_rate(250, 0.01)
            )
            <= 1e-9
        )
        # spec M7: the finite-sample expected count is 250 times that rate.
        assert (
            abs(
                verdict["expected_breaches_finite_sample"]
                - 250 * ORACLE.finite_sample_rate(250, 0.01)
            )
            <= 1e-9
        )
        # spec V3: Kupiec LR agrees within 1e-6.
        assert abs(verdict["kupiec"]["lr"] - oracle_kupiec.lr) <= 1e-6
        # spec V3: Kupiec p-value agrees within 1e-6.
        assert abs(verdict["kupiec"]["p_value"] - oracle_kupiec.p_value) <= 1e-6
        # spec V3: the Kupiec rejection decision is identical.
        assert verdict["kupiec"]["reject_5pct"] is oracle_kupiec.reject
        # spec V3: the Kupiec rejection direction is identical.
        assert verdict["kupiec"]["direction"] == oracle_kupiec.direction
        # spec V3: the Basel verdict is identical.
        assert verdict["basel_zone"] == ORACLE.basel_zone(breaches)
        # spec FR-016 and contracts/http-api.md: verdict context is fixed exact text.
        assert verdict["note"] == FIXED_VERDICT_NOTE


def test_seeded_account_results_arrive_within_five_seconds():
    for account_id, _ in SEEDED_ACCOUNTS:
        started = time.monotonic()
        status, result = _risk_json(
            "GET", "/api/v1/risk/accounts/{}".format(account_id), timeout=6
        )
        elapsed = time.monotonic() - started

        # contracts/http-api.md Outcome → HTTP status: a successful result is 200.
        assert status == 200
        # spec SC-002: each seeded-account current, track-record, and verdict result appears under five seconds.
        assert elapsed < 5.0
        # spec SC-002: the timed response contains the current risk block.
        assert result["current"] is not None
        # spec SC-002: the timed response contains the track-record block.
        assert result["track_record"] is not None
        # spec SC-002: the timed response contains the verdict block.
        assert result["verdict"] is not None


def test_repeated_requests_have_identical_numeric_result_blocks():
    positions = {
        "positions": [
            {"security": "C", "quantity": -2000},
            {"security": "IBM", "quantity": -100},
            {"security": "MS", "quantity": 1000},
        ]
    }

    first_status, first = _risk_json("POST", "/api/v1/risk/positions", positions)
    second_status, second = _risk_json("POST", "/api/v1/risk/positions", positions)

    # contracts/http-api.md Outcome → HTTP status: identical valid positions return OK.
    assert first_status == 200
    # contracts/http-api.md Outcome → HTTP status: identical valid positions return OK.
    assert second_status == 200
    for block in ("current", "track_record", "verdict"):
        # spec SC-008: deterministic comparison covers these blocks and excludes provenance.positions_read_at.
        assert first[block] == second[block]


def test_traderx_baseline_responses_are_preserved():
    with BASELINE_PATH.open(encoding="utf-8") as source:
        baseline = json.load(source)

    # contracts/test-harness.md Baseline responses: the capture contains one responses list.
    assert isinstance(baseline["responses"], list)

    for captured in baseline["responses"]:
        path = captured["path"]
        status, after_body = _request(TRADERX_BASE_URL, "GET", path)

        # spec SC-007: each captured TraderX route preserves its HTTP status.
        assert status == captured["status"]

        if path == "/price-publisher/prices":
            # spec SC-007: the live price lookup keeps the same response shape.
            assert _shape(after_body) == _shape(captured["body"])
            # spec SC-007: the live price lookup keeps the same set of ticker symbols.
            assert _priced_tickers_in(after_body) == _priced_tickers_in(
                captured["body"]
            )
        else:
            # spec SC-007: account and position lookups match baseline when updated is ignored.
            assert _without_updated(after_body) == _without_updated(captured["body"])
