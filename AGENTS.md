# AGENTS.md

## Project Identity
This repository is a quant trading research and execution-support system being refactored from an Antigravity-based codebase into a structured multi-agent architecture.

The target audience is not only engineers but also a product/planning operator who must inspect system behavior, evaluate failures, and guide iterative improvement.

## Core Rules
- Preserve working core logic where reasonable.
- Separate engine logic from UI logic.
- Do not bury key logic in Streamlit-only files.
- Prefer modular, testable engine code.
- All major decisions must produce structured traces.
- Do not rely on hidden internal reasoning as the final source of truth.
- Use explicit evidence, warnings, versioning, and outcomes.

## Mandatory Agents
1. Scanner Agent
2. Aggregation Agent
3. Backtest & Learning Agent
4. Market & News Context Agent
5. PM Planner Agent

## Required Memory Layers
- local short-term memory
- shared working memory
- long-term memory
- artifact store

Keep these conceptually and structurally separate.

## PM Planner Authority
The PM Planner does not directly patch all code arbitrarily.
Instead it:
- reviews outputs from other agents
- performs postmortem analysis
- identifies likely causes of failure
- generates improvement tickets
- requests targeted changes from the responsible agent/module

## Traceability Rules
Every recommendation-worthy candidate must have:
- scanner reasons
- aggregation notes
- backtest diagnostics
- market/news context
- planner decision
- realized outcome placeholder or linked outcome record

## Refactor Strategy
When changing architecture:
1. map current files and dependencies
2. identify reusable engine modules
3. isolate UI-dependent code
4. introduce schemas/contracts
5. implement shared storage
6. add postmortem workflow
7. only then deepen orchestration

## File Design Preferences
- keep schemas explicit
- keep outputs machine-readable
- keep reports human-readable
- avoid giant god-files
- avoid hidden side effects
- avoid tight coupling across scanner/backtest/planner logic

## What to Optimize For
- auditability
- practical iteration speed
- explainability
- lower silent-failure risk
- easier postmortem diagnosis
- safer future automation

## What to Avoid
- clever but untraceable abstractions
- free-form agent chatter as system state
- changing too many responsibilities in one file
- over-reliance on win rate alone
- recommendations detached from current market regime

## If You Are Unsure
Prefer:
- more structure
- more observability
- more version metadata
- more reproducible artifacts
over:
- opaque convenience
- hidden logic
- overly compressed implementations

## Agent Coordination
- Shared discussion thread: `swing-main-0to`
- Read coordination context with `bd comments swing-main-0to`
- Leave handoffs or collision warnings with `bd comment swing-main-0to "..."`
- Keep the thread high-signal only. Use it for:
  - shared-file collision warnings
  - blockers or ownership ambiguity
  - handoffs when stopping mid-task
  - unusually long-running work that needs visibility
- Do not log every normal step there. `bd` issue status and `bd close` should remain the primary source of work state.
- If leaving a thread note, start with an explicit agent prefix such as `[Codex]` or `[Claude]`.
- Acquire `bd merge-slot acquire` before conflict-prone edits or merge resolution
- Release it with `bd merge-slot release` when the risky step is complete

## Issue Shortcut
- Claude's `/issue` workflow is mirrored for Codex through `scripts/issue`.
- Use `scripts/issue` for status, `scripts/issue start <id>` to claim, `scripts/issue end <id> [reason]` to close, `scripts/issue sync` to sync, and `scripts/issue log` for recent closed issues.
- If the user says `/issue ...` to Codex, interpret it as `scripts/issue ...`.

<!-- BEGIN BEADS INTEGRATION v:1 profile:full hash:f65d5d33 -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Dolt-powered version control with native sync
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update <id> --claim --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task atomically**: `bd update <id> --claim`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Quality
- Use `--acceptance` and `--design` fields when creating issues
- Use `--validate` to check description completeness

### Lifecycle
- `bd defer <id>` / `bd supersede <id>` for issue management
- `bd stale` / `bd orphans` / `bd lint` for hygiene
- `bd human <id>` to flag for human decisions
- `bd formula list` / `bd mol pour <name>` for structured workflows

### Auto-Sync

bd automatically syncs via Dolt:

- Each write auto-commits to Dolt history
- Use `bd dolt push`/`bd dolt pull` for remote sync
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

<!-- END BEADS INTEGRATION -->
