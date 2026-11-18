#!/usr/bin/env python3
"""Validator runner for feature 001 (tasks T005, T007-T009; research R9).

Sends one round prompt to qwen3-coder:30b on the local Ollama server and writes the test files
it returns under tests/. Standard library only. Run by the Author from the repository root:

    python3 specs/001-portfolio-var-backtest/validation/validator/run_validator.py --round 1 --dry-run
    python3 specs/001-portfolio-var-backtest/validation/validator/run_validator.py --round 1
    python3 specs/001-portfolio-var-backtest/validation/validator/run_validator.py --round 1 --retry 1 --note note.md

What it guarantees:
  * The prompt is built from exactly the canonical input list (research R9); each input's path and
    SHA-256 is recorded in request.json.
  * Fixed model and options (temperature 0, seed 20261117, num_ctx 65536, num_predict 32768).
    The model digest is checked before the call.
  * The raw response is always saved, even when the run is rejected.
  * Rejected (exit 2, nothing written to tests/) when prompt_eval_count >= 0.9 * num_ctx,
    when done_reason != "stop", or when any returned file path is outside this round's folder.
  * Only fenced blocks whose info string is `python file=tests/<round folder>/<name>.py` are written,
    verbatim. Anything else in the answer is ignored.
  * An accepted run replaces the round folder's contents: files left over from an earlier attempt
    are removed first, and listed in removed.txt.
  * A failed HTTP call is saved as error.json and does not use up a retry: the same command can be
    run again, because a run counts only once response.json exists.
  * --retry is limited to 1 or 2 (at most 2 retries per round, tasks T007-T009).
  * File names: tests/unit/test_unit_*.py, tests/oracle/test_oracle_*.py and oracle_*.py,
    tests/integration/test_integration_*.py; conftest.py allowed once per folder; no subfolders.
  * Round 3 only: every tests/oracle/*.py file (round 2's accepted output) is attached as input 9
    and recorded in request.json; the run stops if tests/oracle/ is empty.
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import posixpath
import re
import sys
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[4]
FEAT = "specs/001-portfolio-var-backtest"
HERE = REPO / FEAT / "validation" / "validator"
PROMPTS = HERE / "prompts"

OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen3-coder:30b"
MODEL_DIGEST = "06c1097efce0431c2045fe7b2e5108366e43bee1b4603a7aded8f21689e90bca"
OPTIONS = {"temperature": 0, "seed": 20261117, "num_ctx": 65536, "num_predict": 32768}

# Canonical validator input list (research R9). Nothing else is sent.
INPUT_FILES = [
    ".specify/memory/constitution.md",
    f"{FEAT}/spec.md",
    f"{FEAT}/contracts/calculation-api.md",
    f"{FEAT}/contracts/http-api.md",
    f"{FEAT}/contracts/data-model.md",
    f"{FEAT}/contracts/test-harness.md",
    f"{FEAT}/data/synthetic_prices_seed20261117.meta.json",
    f"{FEAT}/data/SHA256SUMS",
]
CSV_SAMPLE = f"{FEAT}/data/synthetic_prices_seed20261117.csv"  # header + first 3 + last 3 rows only

ROUNDS = {
    1: {"prompt": "round-1-unit.md", "folder": "tests/unit/", "prefixes": ("test_unit_",)},
    2: {"prompt": "round-2-oracle.md", "folder": "tests/oracle/", "prefixes": ("test_oracle_", "oracle_")},
    3: {"prompt": "round-3-integration.md", "folder": "tests/integration/", "prefixes": ("test_integration_",)},
}
ORACLE_DIR = "tests/oracle"  # round 2's accepted output; attached to round 3 only (input 9)


class InputError(Exception):
    pass

FENCE = re.compile(r"^```python[ \t]+file=(\S+)[ \t]*\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_inputs(rnd: int):
    """Return (text block, list of {path, sha256}) for the canonical inputs (+ oracle files in round 3)."""
    parts, listing = [], []
    for rel in INPUT_FILES:
        data = (REPO / rel).read_bytes()
        listing.append({"path": rel, "sha256": sha256(data)})
        parts.append(f"===== BEGIN FILE: {rel} =====\n{data.decode('utf-8')}\n===== END FILE: {rel} =====")
    csv_bytes = (REPO / CSV_SAMPLE).read_bytes()
    lines = csv_bytes.decode("ascii").splitlines()
    sample = "\n".join([lines[0]] + lines[1:4] + ["... (595 rows omitted; the tests read the full file from its path) ..."] + lines[-3:])
    listing.append({"path": CSV_SAMPLE, "sha256": sha256(csv_bytes), "sent": "header + first 3 + last 3 rows"})
    parts.append(f"===== BEGIN FILE SAMPLE: {CSV_SAMPLE} =====\n{sample}\n===== END FILE SAMPLE: {CSV_SAMPLE} =====")
    if rnd == 3:  # input 9 (round 3 only): round 2's accepted oracle files
        oracle_files = sorted((REPO / ORACLE_DIR).glob("*.py")) if (REPO / ORACLE_DIR).is_dir() else []
        if not oracle_files:
            raise InputError(f"{ORACLE_DIR}/ has no .py files; round 3 needs round 2's accepted output")
        for f in oracle_files:
            rel = str(f.relative_to(REPO))
            data = f.read_bytes()
            listing.append({"path": rel, "sha256": sha256(data), "sent": "round 3 only (oracle, input 9)"})
            parts.append(f"===== BEGIN FILE: {rel} =====\n{data.decode('utf-8')}\n===== END FILE: {rel} =====")
    return "\n\n".join(parts), listing


def build_messages(rnd: int, note_text):
    common = (PROMPTS / "common.md").read_text()
    round_text = (PROMPTS / ROUNDS[rnd]["prompt"]).read_text()
    inputs, listing = build_inputs(rnd)
    user = round_text
    if note_text:
        user += "\n\n## Note from the author for this retry\n\n" + note_text
    user += "\n\n# Inputs\n\n" + inputs
    return [{"role": "system", "content": common}, {"role": "user", "content": user}], listing


def http_json(url, payload=None, timeout=3600):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def check_path(path: str, folder: str, prefixes=()) -> bool:
    """Path must be directly in the round's folder, end in .py, and use the round's file-name prefix
    (or be conftest.py), so every file name is unique across tests/."""
    if path.startswith("/") or "\\" in path or ".." in path.split("/"):
        return False
    norm = posixpath.normpath(path)
    if norm != path or not norm.startswith(folder) or not norm.endswith(".py"):
        return False
    name = norm[len(folder):]
    if "/" in name:
        return False
    return name == "conftest.py" or any(name.startswith(p) for p in prefixes)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, choices=sorted(ROUNDS), required=True)
    ap.add_argument("--dry-run", action="store_true", help="print the input list and prompt size; call nothing, write nothing")
    ap.add_argument("--retry", type=int, choices=[1, 2], help="retry number M (at most 2 per round, tasks T007-T009)")
    ap.add_argument("--note", type=pathlib.Path, help="author's note for the retry (required with --retry)")
    args = ap.parse_args()
    if (args.retry is None) != (args.note is None):
        ap.error("--retry and --note go together")

    note_text = args.note.read_text() if args.note else None
    try:
        messages, listing = build_messages(args.round, note_text)
    except InputError as exc:
        print(f"[error] round {args.round}: {exc}")
        return 2
    folder = ROUNDS[args.round]["folder"]
    chars = sum(len(m["content"]) for m in messages)

    if args.dry_run:
        print(f"round {args.round} -> {folder}")
        print(f"prompt: {chars} characters (~{chars // 4} tokens at 4 chars/token; num_ctx {OPTIONS['num_ctx']})")
        for item in listing:
            print(f"  input {item['sha256'][:12]}  {item['path']}" + (f"  [{item['sent']}]" if "sent" in item else ""))
        print(f"  prompt files: prompts/common.md, prompts/{ROUNDS[args.round]['prompt']}")
        return 0

    out = HERE / f"round-{args.round}"
    if args.retry is not None:
        out = out / f"retry-{args.retry}"
    if (out / "response.json").exists():
        sys.exit(f"[error] {out} already holds a completed run; use --retry M for a new attempt")
    out.mkdir(parents=True, exist_ok=True)

    tags = http_json(f"{OLLAMA}/api/tags", timeout=30)
    digest = next((m["digest"] for m in tags.get("models", []) if m["name"] == MODEL), None)
    if digest != MODEL_DIGEST:
        sys.exit(f"[error] model digest {digest} != expected {MODEL_DIGEST}")
    version = http_json(f"{OLLAMA}/api/version", timeout=30).get("version")

    request = {"model": MODEL, "messages": messages, "stream": False, "options": OPTIONS}
    (out / "prompt.md").write_text("\n\n".join(f"<<<{m['role']}>>>\n{m['content']}" for m in messages))
    if note_text is not None:
        (out / "note.md").write_text(note_text)
    meta = {
        "round": args.round, "retry": args.retry, "folder": folder,
        "model": MODEL, "model_digest": digest, "ollama_version": version, "options": OPTIONS,
        "inputs": listing,
        "prompt_files": {p: sha256((PROMPTS / p).read_bytes()) for p in ["common.md", ROUNDS[args.round]["prompt"]]},
        "started_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (out / "request.json").write_text(json.dumps(meta, indent=2) + "\n")

    try:
        response = http_json(f"{OLLAMA}/api/chat", request)
    except Exception as exc:  # saved, and the same command may be run again
        (out / "error.json").write_text(json.dumps({"error": repr(exc)}, indent=2) + "\n")
        print(f"[failed] Ollama call raised {exc!r}; saved error.json; this attempt is not counted")
        return 2
    (out / "response.json").write_text(json.dumps(response, indent=2, ensure_ascii=False) + "\n")

    used = response.get("prompt_eval_count", 0)
    if used >= 0.9 * OPTIONS["num_ctx"]:
        print(f"[rejected] prompt_eval_count {used} >= 0.9 * num_ctx; prompt may be truncated")
        return 2
    if response.get("done_reason") != "stop":
        print(f"[rejected] done_reason = {response.get('done_reason')!r}, expected 'stop'")
        return 2

    content = response.get("message", {}).get("content", "")
    files = FENCE.findall(content)
    if not files:
        print("[rejected] no `python file=tests/...` blocks found")
        return 2
    bad = [p for p, _ in files if not check_path(p, folder, ROUNDS[args.round]["prefixes"])]
    dupes = {p for p, _ in files if [q for q, _ in files].count(p) > 1}
    if bad or dupes:
        print(f"[rejected] paths outside {folder} or invalid: {bad}; duplicates: {sorted(dupes)}")
        return 2

    removed = sorted(str(f.relative_to(REPO)) for f in (REPO / folder).rglob("*")
                     if f.is_file() and "__pycache__" not in f.parts) if (REPO / folder).exists() else []
    for rel in removed:
        (REPO / rel).unlink()
    (out / "removed.txt").write_text("".join(f"{rel}\n" for rel in removed))

    sums = []
    for path, body in files:
        target = REPO / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
        sums.append(f"{sha256(body.encode())}  {path}")
    (out / "files.sha256").write_text("\n".join(sums) + "\n")
    print(f"wrote {len(files)} files under {folder} (prompt_eval_count {used}, eval_count {response.get('eval_count')})")
    for line in sums:
        print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
