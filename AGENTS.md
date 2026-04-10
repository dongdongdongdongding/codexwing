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

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

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
