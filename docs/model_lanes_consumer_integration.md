# Model-validated lanes — consumer-surface integration

Three live producer lanes sit **alongside** the planner pipeline, not inside it:

| Lane | Producer | Bucket | scan_mode | Contract |
|------|----------|--------|-----------|----------|
| SWING ensemble | `report_swing_ensemble.py` | `swing_ensemble` | SWING | LGBM+XGB+ET → first-touch `ft_5_5`, top ~1%/market, 진입 **종가**, **5거래일** 보유, 목표 +5%, 타이트 손절 X |
| KOSPI intraday | `report_kospi_intraday_swing.py` | `kospi_intraday` | INTRADAY | intraday-path + daily-context ensemble → 3-day +5% MFE touch (`y3`), VWAP≥0 + idx_vol20≥8, top2, 진입 **종가**, **3거래일** 보유, 목표 +5%, 타이트 손절 X |
| KOSDAQ intraday | `report_kosdaq_intraday_vwap_guard.py` | `kosdaq_intraday_3d_t5_vwap_guard` | INTRADAY | LightGBM+isotonic VWAP-guard → 3-day +5% touch, 진입 **15:00**, `p_cal≥0.80` + `pre_vwap_dist≥0`, top2, ≥30억 lane, **3거래일** 보유, 목표 +5%, 타이트 손절 X |

각 레인은 `LANE_PROFILE`에 `scan_mode`/`lane_badge`/`entry_label`(종가 vs 15:00)/`horizon_days`/`prob_label`/`hold_note`를 가진다. 카드·웹은 이 프로필로 SWING(🔵)/INTRADAY(🟢)를 배지로 구분한다.

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

`MODEL_VALIDATED_LANES = {"swing_ensemble", "kospi_intraday", "kosdaq_intraday_3d_t5_vwap_guard"}` is the canonical whitelist, defined in
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

`/kospi_scan` and `/kosdaq_scan` trigger the **planner** SWING pipeline only.

**`/signals`** is the dedicated read command for the model lanes: it surfaces ONLY their picks
(all three lanes — KOSPI intraday → KOSDAQ intraday → swing ensemble, grouped by `bucket_order`),
latest run per lane, as the concise model-lane card —
`build_model_signals_embed` in `renderers.py`, spec `signals` (kind `model_signals_lookup`) in
`commands.py`, handler in `discord_bot.py`, options in `register.py::_command_options`. The lanes
also still appear in the general `/top_deep`, `/archive`, `/runs`.

**Order/badge consistency**: each lane sets `priority_rank = rank = analysis_section_rank = -p`
order, so the scan-result, web Top분석 and Discord views all order picks identically within a run
(web Top분석 shows one `run_id` at a time, so SWING/INTRADAY runs never interleave). Cards carry a
🔵스윙 / 🟢장중 badge + lane name; the web run picker (`scan_display_label`) prefixes scan_mode.
NB the shared `_route_live` derives `scan_mode` per bucket (kospi_intraday → INTRADAY) — do not
hardcode SWING.

An on-demand intraday *scan* command is intentionally not provided — intraday needs post-close
full-session data, so triggering mid-session is meaningless; `/signals` reads the daily-ops output.
