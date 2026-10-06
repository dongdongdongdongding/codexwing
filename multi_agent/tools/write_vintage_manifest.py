"""Fingerprint active pipeline inputs; retain explicit diagnostics for archived research.

The external predecessor crashed opening S/picks_top20 after S was archived onto
an external disk. That obsolete research input prevented recording every active
input, and made every daily batch fail. Active input failures remain failures.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path

TRACKED = {"px_long.parquet": "date", "p2_label.parquet": "date",
           "px_delisted.parquet": "date", "krx_delisting.parquet": "DelistingDate",
           "marcap/marcap-2026.parquet": "Date"}
ARCHIVED = {"S/picks_top20.parquet": "date"}


def entry(cache, rel, datecol):
    import pandas as pd
    path = Path(cache) / rel
    out = {"exists": None}
    try:
        stat = path.stat()
        out.update(exists=True, bytes=stat.st_size,
                   mtime=dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"))
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            digest.update(stream.read(1 << 20))
            stream.seek(max(0, stat.st_size - (1 << 20)))
            digest.update(stream.read(1 << 20))
        frame = pd.read_parquet(path, columns=[datecol])
        newest = pd.to_datetime(frame[datecol], errors="coerce").max()
        if pd.isna(newest):
            raise ValueError("no valid dates")
        if path.stat().st_mtime_ns != stat.st_mtime_ns or path.stat().st_size != stat.st_size:
            raise ValueError("input changed while fingerprinting; retry")
        out.update(sha256_headtail=digest.hexdigest()[:16], max_date=str(newest.date()),
                   rows=len(frame), status="ok")
    except FileNotFoundError as exc:
        out.update(exists=False, status="missing", error=str(exc))
    except (OSError, ValueError) as exc:
        out.update(status="error", error=f"{type(exc).__name__}: {exc}")
    return out


def build_manifest(cache):
    inputs = {rel: {**entry(cache, rel, col), "required": True} for rel, col in TRACKED.items()}
    inputs.update({rel: {**entry(cache, rel, col), "required": False,
                         "role": "archived_research"} for rel, col in ARCHIVED.items()})
    failed = [rel for rel, value in inputs.items() if value["required"] and value["status"] != "ok"]
    return {"version": "pipeline_vintage_v2", "written_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "failed" if failed else "ok", "failed_inputs": failed, "inputs": inputs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path.home() / "research_cache")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    report = build_manifest(args.cache)
    output = args.output_dir or args.cache
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=output, prefix="VINTAGE.", suffix=".tmp",
                                     delete=False, encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        temporary = Path(stream.name)
    try:
        os.replace(temporary, output / "VINTAGE.json")
    finally:
        temporary.unlink(missing_ok=True)
    with (output / "VINTAGE_LOG.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False) + "\n")
    print(json.dumps({"status": report["status"], "failed_inputs": report["failed_inputs"],
                      "archived_unavailable": [k for k in ARCHIVED if report["inputs"][k]["status"] != "ok"]}))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
