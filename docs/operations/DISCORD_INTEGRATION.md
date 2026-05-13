# Discord Remote Control Setup

This integration is intended to make Discord a remote control and result
viewer for the existing scanner. It must not replace the Streamlit UI or fork
the core scoring logic.

## Scope

Discord commands should expose the same operational information as the web UI:

- KOSPI full scan: `max_scan=2000`, `scan_mode=SWING`, `profile=prod`
- KOSDAQ full scan: `max_scan=2000`, `scan_mode=SWING`, `profile=prod`
- Macro refresh
- Top deep analysis history and per-ticker detail
- Scan archive lookup

The Discord view should use the same source artifacts as the web UI:

- `planner_handoff.json`
- `market_scan_results`
- `scan_deep_reports`
- local top-deep JSON reports under `runtime_state/reports/top_deep/`

## Required Discord Values

Create a Discord application in the Discord Developer Portal and add a bot.
Record:

- `DISCORD_BOT_TOKEN`
- `DISCORD_APPLICATION_ID`
- `DISCORD_GUILD_ID`
- `DISCORD_RESULT_CHANNEL_ID`
- `DISCORD_ALLOWED_USER_IDS` or `DISCORD_ALLOWED_ROLE_IDS`

Use a guild-scoped setup first. Global command propagation is slower and is not
needed for a private trading control bot.

Invite the bot to the target guild with both scopes:

```text
bot applications.commands
```

The setup doctor prints a ready-to-open OAuth invite URL after
`DISCORD_APPLICATION_ID` is configured.

## Environment

Add these to `.env.local`:

```bash
DISCORD_BOT_TOKEN=
DISCORD_APPLICATION_ID=
DISCORD_GUILD_ID=
DISCORD_RESULT_CHANNEL_ID=
DISCORD_ALLOWED_USER_IDS=
DISCORD_ALLOWED_ROLE_IDS=
DISCORD_COMMAND_SCOPE=guild
DISCORD_DRY_RUN=1
DISCORD_ENABLE_SCAN_EXECUTION=0
DISCORD_WEB_BASE_URL=http://localhost:8501
```

Keep `DISCORD_DRY_RUN=1` until setup validation passes.

## Validate Setup

```bash
python3 multi_agent/tools/discord_setup_doctor.py
```

The doctor prints:

- missing or malformed Discord IDs
- whether execution is still dry-run
- configured allowlist counts
- the command contract
- web-equivalent result fields Discord must render

The command contract fixes KR scan size at `2000`. Do not expose a user option
for scan count in Discord commands.

## Register Commands

Dry-run first:

```bash
python3 multi_agent/tools/discord_register_commands.py
```

Live guild registration:

```bash
python3 multi_agent/tools/discord_register_commands.py --live
```

Command registration uses Discord REST and does not start the bot process.
If registration returns `403 Missing Access`, invite the bot to the guild with
the doctor invite URL, then run the live registration again.

## Run Bot

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run the bot:

```bash
python3 multi_agent/tools/discord_bot.py
```

The first runnable command should be `/status`. Read-only commands
`/top_deep` and `/archive` read the same local/Supabase-derived artifacts used
by the web UI. `/kospi_scan` and `/kosdaq_scan` acknowledge the full-universe
request but real scan execution remains disabled until both of these are true:

```bash
DISCORD_DRY_RUN=0
DISCORD_ENABLE_SCAN_EXECUTION=1
```

## Command Contract

Initial commands:

```text
/kospi_scan
/kosdaq_scan
/macro_refresh
/top_deep
/archive
/status
```

`/kospi_scan` and `/kosdaq_scan` should defer immediately, run the existing
non-UI pipeline in the background, then post the result summary to
`DISCORD_RESULT_CHANNEL_ID`.

## Result Rendering Requirement

Discord results should mirror the web information structure, adapted to Discord
message limits:

- Embed summary for Top candidates
- Buttons/select menus for ticker detail
- Optional PNG card attachment for near-web visual parity
- CSV/JSON attachment or web link for full archive rows

Required fields:

- rank, ticker, stock name
- decision and decision bucket
- accuracy/OOS
- day change
- loss risk
- risk flags and rationale
- final action
- entry condition
- stop/exclusion condition
- Entry/TP/SL/Hold
- stock quality score/grade
- upside room score/grade
- entry timing score/grade
- chase risk level and chase filters
- run ID and archive source reference

## Safety Rules

- Restrict command execution by Discord user ID or role ID.
- Keep Discord bot code outside `app.py`.
- Keep scanner/planner scoring untouched.
- Use `max_scan=2000` for both KOSPI and KOSDAQ.
- Use one scan lock so two full KR scans cannot run at the same time.
- Do not print or log `DISCORD_BOT_TOKEN`.
- Keep scan execution disabled until command registration and read-only
  responses are verified in the private guild.
