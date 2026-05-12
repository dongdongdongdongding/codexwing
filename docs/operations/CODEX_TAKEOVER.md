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

- Existing uncommitted `runtime_state/` changes predate this takeover cleanup and should be treated as user/runtime artifacts until separately claimed.
- No Git remote is configured in this checkout, so the mandatory `git push` completion step cannot succeed until a remote is added.
- Use `bd` issues, not markdown task lists, for follow-up work.
