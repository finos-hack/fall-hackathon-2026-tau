"""RiskResult assembly: provenance, outcome precedence, and the current / track_record / verdict
blocks (contracts/http-api.md, contracts/data-model.md). All figures use SYNTHETIC prices."""
import datetime as dt
import json
import math
import re
from typing import Dict, List, Optional, Tuple

from . import core, traderx_client
from .prices import DATA_FILE, LABEL, SEED, PriceHistory

PARAMS = core.Params()  # lam 0.94, pool 250, warmup 100, p 0.01 (fixed for this feature)
CONFIDENCE = 0.99
HORIZON_DAYS = 1
BACKTEST_DAYS = 250
METHOD = "filtered historical simulation, EWMA λ=0.94"
QUANTILE_RULE = "linear interpolation, position (n−1)p"
SOURCE_ACCOUNT = "TraderX account"
SOURCE_CALLER = "caller-supplied"

VERDICT_NOTE = (
    "A correct implementation of this method breaches about 1.39% of days (3.5 per 250), not 1%, "
    "because the 1% quantile of a 250-day pool sits between the 3rd and 4th worst outcomes. Such a "
    "model reaches the amber zone or worse roughly a quarter of the time, so amber alone does not "
    "prove the model wrong. Kupiec is tested against the nominal 1%."
)

STATUS = {
    "OK": 200,
    "NO_OPEN_POSITIONS": 200,
    "ACCOUNT_NOT_FOUND": 404,
    "MISSING_PRICE_HISTORY": 422,
    "ZERO_VOLATILITY": 422,
    "POSITIONS_UNAVAILABLE": 503,
    "INVALID_REQUEST": 400,
}

ACCOUNT_ID = re.compile(r"[0-9]{1,18}")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def provenance(history: PriceHistory, source: str, read_at: Optional[str]) -> dict:
    """Every field in the data-model Provenance table (FR-015), on every response."""
    return {
        "data": LABEL,
        "synthetic": True,
        "seed": SEED,
        "data_file": DATA_FILE,
        "data_sha256": history.sha256,
        "method": METHOD,
        "lambda": PARAMS.lam,
        "pool_size": PARAMS.pool,
        "warmup": PARAMS.warmup,
        "confidence": CONFIDENCE,
        "horizon_days": HORIZON_DAYS,
        "quantile_rule": QUANTILE_RULE,
        "as_of_date": history.as_of,
        "position_source": source,
        "positions_read_at": read_at,
    }


def _envelope(outcome: str, message: str, prov: dict, account: Optional[dict] = None,
              missing: Optional[List[str]] = None, blocks: Optional[dict] = None) -> Tuple[int, dict]:
    result = {"outcome": outcome, "message": message, "provenance": prov}
    if account is not None:
        result["account"] = account
    result["current"] = None
    result["track_record"] = None
    result["verdict"] = None
    if blocks is not None:
        result.update(blocks)
    if missing is not None:
        result["missing_securities"] = missing
    return STATUS[outcome], result


def _invalid(message: str, prov: dict) -> Tuple[int, dict]:
    return _envelope("INVALID_REQUEST", message, prov)


def _is_finite_number(value) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def parse_caller_body(raw: bytes) -> Tuple[Optional[List[dict]], Optional[str]]:
    """Caller-supplied body rules (FR-020). Returns (positions, None) or (None, error message)."""
    try:
        body = json.loads(raw.decode("utf-8")) if raw else None
    except (UnicodeDecodeError, ValueError):
        return None, "The request body is not valid JSON."
    if not isinstance(body, dict) or not isinstance(body.get("positions"), list):
        return None, 'The body must be a JSON object with a "positions" list.'
    seen = set()
    positions = []
    for index, item in enumerate(body["positions"]):
        if not isinstance(item, dict):
            return None, f"Position {index} is not an object."
        security, quantity = item.get("security"), item.get("quantity")
        if not isinstance(security, str) or not security:
            return None, f"Position {index} needs a non-empty security."
        if not _is_finite_number(quantity):
            return None, f"Position {index} ({security}) needs a finite numeric quantity."
        if security in seen:
            return None, f"Security {security} appears more than once."
        seen.add(security)
        positions.append({"security": security, "quantity": quantity})
    return positions, None


def _current_block(history: PriceHistory, positions: Dict[str, float], current_var: float) -> dict:
    rows = []
    net = 0.0
    for security in sorted(positions):
        quantity = positions[security]
        price = history.closes[security][-1]  # as-of close, s = N
        market_value = quantity * price
        net += market_value
        rows.append({"security": security, "quantity": quantity, "price": price,
                     "market_value": market_value})
    return {"var_usd": current_var, "data_as_of": history.as_of,
            "forecast_for": history.forecast_for, "positions": rows, "net_market_value": net}


def _track_record(history: PriceHistory, bt: core.Backtest) -> List[dict]:
    if len(bt.rows) != BACKTEST_DAYS:
        raise AssertionError(f"expected B = {BACKTEST_DAYS} backtest rows, got {len(bt.rows)}")
    return [{"day": row.t, "date": history.dates[row.t], "forecast_var_usd": row.forecast_var,
             "realised_pnl_usd": row.pnl, "breach": row.breach} for row in bt.rows]


def _verdict(bt: core.Backtest) -> dict:
    observations = len(bt.rows)
    breaches = sum(1 for row in bt.rows if row.breach)
    test = core.kupiec(breaches, observations, PARAMS.p)
    rate = core.finite_sample_rate(PARAMS.pool, PARAMS.p)
    return {
        "observations": observations,
        "breaches": breaches,
        "breach_rate": breaches / observations,
        "expected_breaches_nominal": observations * PARAMS.p,
        "expected_breaches_finite_sample": observations * rate,
        "finite_sample_rate": rate,
        "kupiec": {
            "lr": test.lr,
            "p_value": test.p_value,
            "null_p": PARAMS.p,
            "critical_value": core.KUPIEC_CRITICAL_5PCT,
            "reject_5pct": test.reject,
            "direction": test.direction,
        },
        "basel_zone": core.basel_zone(breaches),
        "note": VERDICT_NOTE,
    }


def risk_for_positions(history: PriceHistory, raw_positions: List[dict], prov: dict,
                       account: Optional[dict] = None) -> Tuple[int, dict]:
    """Outcome precedence steps 4-8 (http-api.md) on an already-read position list."""
    positions: Dict[str, float] = {}
    for item in raw_positions:  # step 4: drop zero quantities
        if item["quantity"] == 0:
            continue
        positions[item["security"]] = positions.get(item["security"], 0) + item["quantity"]
    positions = {s: q for s, q in positions.items() if q != 0}
    if not positions:  # step 5
        return _envelope("NO_OPEN_POSITIONS",
                         "There are no open positions, so there is no risk figure to compute.",
                         prov, account)
    missing = sorted(s for s in positions if s not in history.closes)
    if missing:  # step 6
        return _envelope("MISSING_PRICE_HISTORY",
                         "No synthetic price history for: " + ", ".join(missing) + ".",
                         prov, account, missing=missing)
    pnl = core.pnl_series(history.closes, positions)
    try:
        bt = core.backtest(pnl, PARAMS)
    except core.ZeroVolatilityError:  # step 7
        return _envelope("ZERO_VOLATILITY",
                         "Every warm-up P&L value is zero, so the volatility filter cannot start.",
                         prov, account)
    blocks = {"current": _current_block(history, positions, bt.current_var),
              "track_record": _track_record(history, bt),
              "verdict": _verdict(bt)}
    return _envelope("OK", "One-day 99% VaR computed on SYNTHETIC price history.",
                     prov, account, blocks=blocks)


def account_result(history: PriceHistory, account_id_text: str) -> Tuple[int, dict]:
    """GET /api/v1/risk/accounts/{accountId}: precedence steps 1-8."""
    if not ACCOUNT_ID.fullmatch(account_id_text or ""):  # step 1
        return _invalid("accountId must be a decimal integer.",
                        provenance(history, SOURCE_ACCOUNT, None))
    account_id = int(account_id_text)
    try:  # step 2: either lookup failing gives POSITIONS_UNAVAILABLE
        account = traderx_client.get_account(account_id)
        positions = traderx_client.get_positions(account_id)
        read_at = utc_now()
    except traderx_client.TraderXUnavailable as exc:
        return _envelope("POSITIONS_UNAVAILABLE", f"TraderX could not be reached: {exc}",
                         provenance(history, SOURCE_ACCOUNT, None))
    if account is None:  # step 3
        return _envelope("ACCOUNT_NOT_FOUND", f"Account {account_id} does not exist in TraderX.",
                         provenance(history, SOURCE_ACCOUNT, None))
    return risk_for_positions(history, positions, provenance(history, SOURCE_ACCOUNT, read_at),
                              account)


def caller_result(history: PriceHistory, raw_body: bytes) -> Tuple[int, dict]:
    """POST /api/v1/risk/positions (FR-020): body rules, then precedence steps 4-8."""
    prov = provenance(history, SOURCE_CALLER, None)
    positions, error = parse_caller_body(raw_body)
    if error:
        return _invalid(error, prov)
    return risk_for_positions(history, positions, prov)


def accounts_list(history: PriceHistory) -> Tuple[int, dict]:
    """GET /api/v1/accounts: the TraderX account list for the picker."""
    try:
        accounts = traderx_client.list_accounts()
        read_at = utc_now()
    except traderx_client.TraderXUnavailable as exc:
        return _envelope("POSITIONS_UNAVAILABLE", f"TraderX could not be reached: {exc}",
                         provenance(history, SOURCE_ACCOUNT, None))
    return 200, {"accounts": accounts, "provenance": provenance(history, SOURCE_ACCOUNT, read_at)}
