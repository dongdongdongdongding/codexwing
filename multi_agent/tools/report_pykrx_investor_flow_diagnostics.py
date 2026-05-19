from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.kr_investor_flow_diagnostics import (
    build_pykrx_investor_flow_investigation,
    render_pykrx_investigation_markdown,
)


def main() -> None:
    report = build_pykrx_investor_flow_investigation()
    out_dir = Path("runtime_state/reports/validation")
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "pykrx_investor_flow_diagnostics.json"
    md_path = out_dir / "pykrx_investor_flow_diagnostics.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_pykrx_investigation_markdown(report), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "decision": report["decision"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
