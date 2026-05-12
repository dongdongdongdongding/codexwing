# Codex Takeover

Codex is the primary worker for this repository. Root-level legacy-agent instructions were removed to avoid conflicting operating protocols.

## Operating Source Of Truth

- Project rules: `AGENTS.md`
- Issue state: `bd` through `scripts/issue`
- Shared coordination: `bd comments swing-main-0to`
- High-risk edit lock: `bd merge-slot acquire` / `bd merge-slot release`

Use the shared coordination thread only for collision warnings, blockers, ownership ambiguity, handoffs, or unusually long-running work. Routine progress belongs in the claimed `bd` issue and final work summary.

## Beads Validation Commands

Run these from the repository root:

```bash
scripts/issue
bd dolt test
bd dolt status
bd doctor --json
```

Known environment detail: `/Users/dongdong/Desktop/codex_swing/swing-main` is a symlink to `/Users/dongdong/Projects/codex_swing/swing-main`, so some beads diagnostics may display the Desktop path while the Git toplevel remains the Projects path.

## Current Handoff Notes

- Git remote is configured and push-tested:
  - code: `git@github-codexwing:dongdongdongdongding/codexwing.git`
  - beads: `git+ssh://git@github-dolt-beads/dongdongdongdongding/dolt.git`
- The 2026-05-13 runtime cleanup removed generated `runtime_state` files from the Git index while preserving local files on disk.
- Treat ignored `runtime_state/artifacts`, `runtime_state/shared_working`, context caches, top-deep per-run reports, and large archive datasets as local/generated artifacts.
- Curated learning, validation, trading, and selected long-term summary reports may be tracked when they are release or planning evidence.
- Use `bd` issues, not markdown task lists, for follow-up work.

## Current UI Server

The Streamlit operator UI is normally run from the repository root:

```bash
python3 -m streamlit run app.py --server.port 8501
```

Local URL:

```text
http://localhost:8501
```
