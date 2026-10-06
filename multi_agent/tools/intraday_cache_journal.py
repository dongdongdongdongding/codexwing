"""Immutable checkpoints and append deltas for recoverable intraday caches.

Restoration produces the exact logical DataFrame, not original Parquet bytes.
Every stored artifact is SHA256 verified before it is used. Old evidence is
never deleted; an external cache replacement starts a new checkpoint branch.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid

import pandas as pd
import pyarrow as pa


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def atomic_write(path, writer):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".backfill-", dir=path.parent)
    os.close(fd)
    temp = Path(name)
    try:
        writer(temp)
        with temp.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temp, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temp.unlink(missing_ok=True)


def save_json(path, value):
    atomic_write(path, lambda temp: temp.write_text(json.dumps(value, ensure_ascii=False, indent=2)))


def frame_digest(frame):
    # Pandas metadata contains the installed pyarrow version; exclude that
    # incidental value while retaining explicit index/column identity below.
    table = pa.Table.from_pandas(frame, preserve_index=True).replace_schema_metadata(None).combine_chunks()
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    identity = json.dumps({"columns": list(frame.columns), "index_names": list(frame.index.names),
                           "dtypes": [str(x) for x in frame.dtypes], "index_dtype": str(frame.index.dtype)},
                          sort_keys=True).encode()
    return hashlib.sha256(identity + sink.getvalue().to_pybytes()).hexdigest()


def reference(path):
    return {"path": str(path.resolve()), "sha256": digest(path)}


def checked_path(ref):
    path = Path(ref["path"])
    if not ref.get("sha256") or digest(path) != ref["sha256"]:
        raise ValueError("journal_artifact_hash_mismatch")
    return path


def restore_state(state):
    """Read-only replay; never trust a partial or damaged chain."""
    nodes, visited = [], set()
    while state is not None:
        path = checked_path(state)
        if str(path) in visited:
            raise ValueError("journal_cycle")
        visited.add(str(path))
        node = json.loads(path.read_text())
        if node.get("version") != 1 or node.get("kind") not in {"checkpoint", "append"}:
            raise ValueError("unknown_journal_format")
        nodes.append(node)
        state = node.get("parent") if node["kind"] == "append" else None
    parts = []
    for node in reversed(nodes):
        data = pd.read_parquet(checked_path(node["data"]))
        parts.append(data)
    if not parts:
        return None
    frame = pd.concat(parts).sort_index() if len(parts) > 1 else parts[0]
    if frame.index.has_duplicates:
        raise ValueError("journal_delta_overlaps_existing_rows")
    if frame_digest(frame) != nodes[0]["frame_sha256"]:
        raise ValueError("journal_reconstruction_mismatch")
    return frame


def write_node(directory, kind, data_path, frame, parent=None):
    node = {"version": 1, "kind": kind, "data": reference(data_path),
            "parent": parent, "frame_sha256": frame_digest(frame), "rows": len(frame)}
    path = directory/f"{uuid.uuid4().hex}.json"
    save_json(path, node)
    return reference(path)


def prepare_states(path, old, combined, before_sha):
    """Persist and verify recovery evidence before cache replacement."""
    directory = path.parent/".backfill/journal"/path.stem
    directory.mkdir(parents=True, exist_ok=True)
    head_path = directory/"head.json"
    head = json.loads(head_path.read_text()) if head_path.exists() else {}
    before_state = None
    if old is not None:
        if head.get("file_sha256") == before_sha and head.get("state"):
            before_state = head["state"]
        else:
            backup = directory/f"{uuid.uuid4().hex}.checkpoint.parquet"
            atomic_write(backup, lambda temp: shutil.copyfile(path, temp))
            if digest(backup) != before_sha:
                raise ValueError("backup_or_source_changed")
            before_state = write_node(directory, "checkpoint", backup, old)
        restored = restore_state(before_state)
        if not restored.equals(old):
            raise ValueError("journal_before_reconstruction_mismatch")
    delta = combined if old is None else combined.loc[~combined.index.isin(old.index)]
    replay = pd.concat([old, delta]).sort_index() if old is not None else delta
    # Schema changes that cannot be represented losslessly need a new full
    # checkpoint. This is exceptional; normal additions store only new rows.
    append = replay.equals(combined)
    data = delta if append else combined
    data_path = directory/f"{uuid.uuid4().hex}.{'delta' if append else 'checkpoint'}.parquet"
    atomic_write(data_path, lambda temp: data.to_parquet(temp))
    if not pd.read_parquet(data_path).equals(data):
        raise ValueError("journal_data_verification_failed")
    after_state = write_node(directory, "append" if append else "checkpoint", data_path,
                             combined, before_state if append else None)
    if not restore_state(after_state).equals(combined):
        raise ValueError("journal_after_reconstruction_mismatch")
    return {"before_state": before_state, "after_state": after_state,
            "head_path": str(head_path), "kind": "append" if append else "checkpoint",
            "rows_stored": len(data), "data_bytes": data_path.stat().st_size}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record", type=Path, required=True, help="Collection audit JSON")
    ap.add_argument("--state", choices=["before", "after"], default="before")
    ap.add_argument("--output", type=Path, required=True, help="New recovery file; never overwrite cache")
    args = ap.parse_args()
    record = json.loads(args.record.read_text())
    frame = restore_state(record["recovery"][args.state+"_state"])
    if frame is None:
        raise ValueError("requested_state_had_no_file")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".restore-", dir=args.output.parent)
    os.close(fd)
    temp = Path(name)
    try:
        frame.to_parquet(temp)
        if not pd.read_parquet(temp).equals(frame):
            raise ValueError("recovery_export_verification_failed")
        with temp.open("rb") as stream:
            os.fsync(stream.fileno())
        os.link(temp, args.output)  # Atomic create; an existing output is refused.
    finally:
        temp.unlink(missing_ok=True)
    print(json.dumps({"rows": len(frame), "frame_sha256": frame_digest(frame),
                      "output": str(args.output), "source_state": args.state}))


if __name__ == "__main__":
    main()
