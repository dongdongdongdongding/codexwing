# Model-validated lanes — consumer-surface integration

Two live producer lanes sit **alongside** the planner pipeline, not inside it:

| Lane | Producer | Bucket | Contract |
|------|----------|--------|----------|
| SWING ensemble | `report_swing_ensemble.py` | `swing_ensemble` | LGBM+XGB+ET → first-touch `ft_5_5`, top ~1%/market, **5거래일** 종가 보유, 목표 +5%, 타이트 손절 X |
| KOSPI intraday | `report_kospi_intraday_swing.py` | `kospi_intraday` | intraday-path + daily-context ensemble → 3-day +5% MFE touch (`y3`), VWAP≥0 + idx_vol20≥8 guards, top2, **3거래일** 종가 보유, 목표 +5%, 타이트 손절 X |

Both run inside `run_daily_ops.sh` (KOSPI intraday needs post-close full-session KIS minute bars,
so it is **not** an on-demand mid-session scan). They dual-write the SAME picks to
`market_scan_results` (archive/learning) and directly to `scan_deep_reports` (web/Discord surface)
via the shared `_route_live`, bypassing `generate_and_store_top_deep_reports` (which would re-run the
admission model and reclassify them to `admission_near_miss` / drop KOSDAQ).

## Why these lanes get a dedicated interpretation

They are validated by **backtested forward touch-probability + walk-forward OOS**, not by the legacy
chart / non-chart operational axes (flow / theme / news), which are structurally absent for
price/intraday-only models. The legacy gate would otherwise demote every pick to
`운용 보류 / AVOID_WEAK_SUPPORT` even though the model says BUY.

`MODEL_VALIDATED_LANES = {"swing_ensemble", "kospi_intraday"}` is the canonical whitelist, defined in
`modules/operational_candidate_scoring.py` (lowest module in the dep graph). Two gates branch on it:

- `build_operational_candidate_score` → returns `MODEL_BUY` (used by `ui_helpers` / `top_deep` which
  read `operational_action_*` directly).
- `build_candidate_interpretation` → returns `build_model_lane_interpretation` (BUY, entry=close,
  +5% target, hold N days, no tight stop, hit-probability, thesis). Per-lane copy lives in `LANE_PROFILE`.

Planner picks (no matching bucket) are untouched — they keep the full legacy gate.

## Consumer surfaces

- **Web 정밀분석** (`ui_helpers`): recomputes both gates → correct automatically.
- **Web top_deep** / **Discord top_deep+archive**: read the STORED `candidate_interpretation`. New runs
  store the correct one; already-stored rows must be re-routed (reconstruct picks from
  `market_scan_results` → `_route_live`) to overwrite the stored interpretation.
- **Discord message**: model-lane picks render a concise 4-line card (`_field_value_model_lane`)
  instead of the ~17-line legacy block (which was mostly `-` for these lanes).

## Commands

`/kospi_scan` and `/kosdaq_scan` trigger the **planner** SWING pipeline only. The model lanes are
**read** via `/top_deep`, `/archive`, `/runs` (their picks are in `scan_deep_reports`). An on-demand
intraday scan command is intentionally not provided — intraday requires post-close data.
