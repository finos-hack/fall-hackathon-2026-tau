"""Frozen SYNTHETIC price history (spec M1, FR-014; contracts/data-model.md SyntheticPriceHistory).

The file is generated from seed 20261117 and is NOT real market data. The service refuses to start
unless the file's SHA-256 matches the pinned value.
"""
import csv
import datetime as dt
import hashlib
import io
import os
import pathlib
from dataclasses import dataclass
from typing import Dict, List, Optional

FILE_NAME = "synthetic_prices_seed20261117.csv"
DATA_FILE = "specs/001-portfolio-var-backtest/data/" + FILE_NAME  # as reported in provenance
EXPECTED_SHA256 = "9ea2eab18bc0bf108fffb90245fd7f51a07e0fa16e52d49564e20c50e0718ce3"
LABEL = "SYNTHETIC price history - not real market data"
SEED = 20261117
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "specs/001-portfolio-var-backtest/data"


class PriceFileError(RuntimeError):
    """The price file is missing, malformed, or its checksum does not match."""


@dataclass(frozen=True)
class PriceHistory:
    dates: List[str]  # ISO dates, index s = 0 ... N
    closes: Dict[str, List[float]]  # ticker -> C_0 ... C_N
    tickers: List[str]  # snapshot (file) order
    sha256: str
    as_of: str  # dates[N]
    forecast_for: str  # next weekday after as_of


def next_weekday(iso_date: str) -> str:
    day = dt.date.fromisoformat(iso_date) + dt.timedelta(days=1)
    while day.weekday() >= 5:
        day += dt.timedelta(days=1)
    return day.isoformat()


def data_path(data_dir: Optional[str] = None) -> pathlib.Path:
    configured = data_dir or os.environ.get("RISK_DATA_DIR")
    base = pathlib.Path(configured) if configured else DEFAULT_DATA_DIR
    if not base.is_absolute():
        base = REPO_ROOT / base
    return base / FILE_NAME


def load(data_dir: Optional[str] = None) -> PriceHistory:
    path = data_path(data_dir)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PriceFileError(f"cannot read {path}: {exc}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise PriceFileError(f"{path} has sha256 {digest}, expected {EXPECTED_SHA256}")
    reader = csv.reader(io.StringIO(raw.decode("ascii")))
    header = next(reader)
    if not header or header[0] != "date":
        raise PriceFileError(f"{path}: first column must be 'date'")
    tickers = header[1:]
    dates: List[str] = []
    closes: Dict[str, List[float]] = {t: [] for t in tickers}
    for row in reader:
        if not row:
            continue
        if len(row) != len(header):
            raise PriceFileError(f"{path}: row {len(dates) + 1} has {len(row)} fields")
        dates.append(row[0])
        for ticker, text in zip(tickers, row[1:]):
            closes[ticker].append(float(text))
    as_of = dates[-1]
    return PriceHistory(dates=dates, closes=closes, tickers=tickers, sha256=digest,
                        as_of=as_of, forecast_for=next_weekday(as_of))
