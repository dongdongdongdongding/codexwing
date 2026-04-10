from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List

import requests


def _load_local_env() -> None:
    for candidate in (Path(".env.local"), Path(".env")):
        if not candidate.exists():
            continue
        try:
            for raw_line in candidate.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = value
        except Exception:
            continue


def _load_sql_statements(sql_path: Path) -> List[str]:
    raw = sql_path.read_text(encoding="utf-8")
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    statements = [chunk.strip() for chunk in cleaned.split(";") if chunk.strip()]
    return statements


def main() -> int:
    _load_local_env()
    parser = argparse.ArgumentParser(description="Apply SQL schema to Supabase via Management API.")
    parser.add_argument(
        "--project-ref",
        type=str,
        default=os.getenv("SUPABASE_PROJECT_REF", "ichzaklvmicgyvjxpxeo"),
        help="Supabase project ref.",
    )
    parser.add_argument(
        "--sql",
        type=str,
        default="docs/migration/supabase_agent_tables.sql",
        help="SQL file path.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sql_path = Path(args.sql)
    if not sql_path.exists():
        raise SystemExit(f"SQL file not found: {sql_path}")

    statements = _load_sql_statements(sql_path)
    if not statements:
        raise SystemExit("No SQL statements parsed.")

    if args.dry_run:
        print(json.dumps({"project_ref": args.project_ref, "statement_count": len(statements)}, ensure_ascii=False, indent=2))
        return 0

    access_token = os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise SystemExit("SUPABASE_ACCESS_TOKEN is required (Supabase Personal Access Token).")

    endpoint = f"https://api.supabase.com/v1/projects/{args.project_ref}/database/query"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    applied = 0
    for stmt in statements:
        resp = requests.post(endpoint, headers=headers, json={"query": stmt}, timeout=30)
        if resp.status_code >= 300:
            raise SystemExit(
                f"Failed at statement {applied+1}/{len(statements)}\nstatus={resp.status_code}\nbody={resp.text}"
            )
        applied += 1

    print(json.dumps({"project_ref": args.project_ref, "applied_statements": applied}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
