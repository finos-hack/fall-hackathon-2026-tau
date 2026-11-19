"""HTTP server for the risk service (contracts/http-api.md). Standard library only.

Run: PYTHONPATH=risk-service python3 -m risk_service.server
Binds RISK_BIND_HOST (default 127.0.0.1; the container image sets 0.0.0.0 and compose publishes the
port on 127.0.0.1 only) and RISK_PORT (default 18110). Exits non-zero if the price file checksum
does not match. All figures are computed on SYNTHETIC price history, not real market data.
"""
import json
import mimetypes
import os
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

from . import prices, results

STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"
MAX_BODY = 1 << 20
ACCOUNT_PREFIX = "/api/v1/risk/accounts/"


class Handler(BaseHTTPRequestHandler):
    server_version = "risk-service/001"
    history: prices.PriceHistory = None  # set at startup

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, allow_nan=False, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _static(self, path: str) -> None:
        name = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (STATIC_DIR / name).resolve()
        if STATIC_DIR not in target.parents or not target.is_file():
            self._json(404, {"error": "not found"})
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type.endswith("javascript"):
            content_type += "; charset=utf-8"
        self._send(200, target.read_bytes(), content_type)

    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        path = urlsplit(self.path).path
        history = self.history
        if path == "/health":
            self._json(200, {"status": "ok", "data_sha256": history.sha256, "synthetic": True})
        elif path == "/api/v1/accounts":
            self._json(*results.accounts_list(history))
        elif path.startswith(ACCOUNT_PREFIX):
            self._json(*results.account_result(history, unquote(path[len(ACCOUNT_PREFIX):])))
        elif path == "/api/v1/risk/positions":
            self._json(405, {"error": "use POST"})
        else:
            self._static(path)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path != "/api/v1/risk/positions":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self._json(*results.caller_result(self.history, b"\xff"))  # INVALID_REQUEST
            return
        self._json(*results.caller_result(self.history, self.rfile.read(length)))


def main() -> int:
    try:
        history = prices.load()
    except prices.PriceFileError as exc:
        print(f"[risk-service] refusing to start: {exc}", file=sys.stderr)
        return 1
    Handler.history = history
    host = os.environ.get("RISK_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("RISK_PORT", "18110"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"[risk-service] {prices.LABEL}; sha256 {history.sha256}; as of {history.as_of}; "
          f"listening on {host}:{port}", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
