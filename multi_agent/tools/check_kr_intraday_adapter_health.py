from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.kr_intraday_adapter_contract import build_kr_intraday_adapter_health


def main() -> None:
    print(json.dumps(build_kr_intraday_adapter_health(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
