"""Read-only TraderX client: GET calls only, urllib, 5 s timeout (contracts/http-api.md)."""
import json
import os
import urllib.error
import urllib.request
from typing import List, Optional

TIMEOUT_S = 5.0


class TraderXUnavailable(RuntimeError):
    """Connection error, timeout, 5xx, or an unreadable answer from a TraderX service."""


def _account_url() -> str:
    return os.environ.get("TRADERX_ACCOUNT_URL", "http://127.0.0.1:18088").rstrip("/")


def _position_url() -> str:
    return os.environ.get("TRADERX_POSITION_URL", "http://127.0.0.1:18090").rstrip("/")


def _get_json(url: str, allow_404: bool = False):
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and allow_404:
            return None
        raise TraderXUnavailable(f"GET {url} returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:  # refused, DNS, timeout
        raise TraderXUnavailable(f"GET {url} failed: {exc}") from exc
    try:
        return json.loads(body.decode("utf-8"))
    except ValueError as exc:
        raise TraderXUnavailable(f"GET {url} returned a body that is not JSON") from exc


def get_account(account_id: int) -> Optional[dict]:
    """The account as {id, displayName}, or None when the account service answers 404."""
    data = _get_json(f"{_account_url()}/account/{account_id}", allow_404=True)
    if data is None:
        return None
    if not isinstance(data, dict) or "id" not in data:
        raise TraderXUnavailable("account service returned an unexpected body")
    return {"id": data["id"], "displayName": data.get("displayName")}


def get_positions(account_id: int) -> List[dict]:
    """The account's positions as [{security, quantity}] (empty list for unknown accounts)."""
    data = _get_json(f"{_position_url()}/positions/{account_id}")
    if not isinstance(data, list):
        raise TraderXUnavailable("position service returned an unexpected body")
    positions = []
    for item in data:
        if not isinstance(item, dict) or "security" not in item or "quantity" not in item:
            raise TraderXUnavailable("position service returned an unexpected item")
        positions.append({"security": item["security"], "quantity": item["quantity"]})
    return positions


def list_accounts() -> List[dict]:
    data = _get_json(f"{_account_url()}/account/")
    if not isinstance(data, list):
        raise TraderXUnavailable("account service returned an unexpected list")
    return [{"id": a.get("id"), "displayName": a.get("displayName")} for a in data if isinstance(a, dict)]
