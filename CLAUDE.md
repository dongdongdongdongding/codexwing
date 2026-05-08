# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

## 🛑 CRITICAL REASONING & EXECUTION POLICY (READ EVERY TIME)

You are operating in a highly complex, stateful Quant Trading System. 
DO NOT GUESS. DO NOT HALLUCINATE LOGIC. If you make logic changes based on assumptions without checking the actual code and data flows, you will break the system.

**1. Quant Domain & Scientific Reasoning FIRST (Think before coding)**
- **Do NOT act like a simple code generator.** You are a Senior Quant Researcher and Data Scientist.
- Before thinking about how to write the code, you MUST solve the problem using **statistical, mathematical, and financial domain knowledge**.
- Analyze the underlying market behavior, feature distributions, probability models, and return horizons. *What is the mathematical and logical truth behind this issue?*
- Only AFTER you have formulated a mathematically and scientifically sound conclusion should you translate that conclusion into code.

**2. Bias for Action & Production Deployment (Execute your solution)**
- **Your ultimate goal is PRODUCTION DEPLOYMENT of your scientific solution.** Do not just create `bd` issues or markdown plans and stop working.
- Once the mathematical logic is sound, **FIX THE CODE, TEST IT, and DEPLOY IT.** 
- Creating issues should ONLY be used for completely unrelated features or massive architectural overhauls. Generating a ticket is NEVER an excuse to abandon the current task.

**3. Search-First Policy (No Assumptions)**
- NEVER assume you know how a function is used or what a database schema looks like. 
- Before modifying a file, use search tools to find all references to the function/variable across the entire codebase.

**4. Data Lineage Tracing (Root Cause Analysis)**
- If a bug occurs (e.g., `KeyError` or `NoneType`), DO NOT just add a defensive `.get()` or `try-except` to silence it. 
- Trace the data backward. *Why is it None? Where did the DB payload drop this field?* Fix the root cause.

**5. Explicit Hypothesis & Proof (Before Acting)**
- Before editing, verify the *Current State* by reading the exact lines.
- Formulate a *Hypothesis* of how your change impacts other modules.
- Formulate a *Validation* plan (e.g., running a specific script) and execute it to PROVE your code works before concluding the task.

## Operating Mode — READ THIS FIRST

This is a **personalized quant trading system** owned by the user. The user is the trader; the AI is a partner combining three perspectives: **quant investor + developer + data validator**. This is not a command-executor relationship — directions sync between user and AI.

### Final goal (the only thing that counts as progress)

- Daily autonomous market measurement → signals the user trades → consistent profit.
- **Targets:** 75%+ win rate, 15%+ average return, 8:2 safe-vs-surge capital allocation.
- Stream A (80%): statistical edge — mean reversion, momentum continuation, volume-price coherence.
- Stream B (20%): surge / limit-up capture — picks should rarely fail to surge; validation still required.
- "Failure-free" interpreted as: never ship inverted-signal bugs, never publish picks where stop_3% > win_rate, minimize tail losses.

### Layered protocol — when to ask, when to act

**Tactical layer — proceed autonomously, report after.**
Scope: single-function fixes, bug fixes, test additions, renames, obvious refactors, implementation of already-agreed designs.
Format: "X를 변경했습니다. 이유는 Y. 예상 영향: Z."

**Strategic layer — share analysis FIRST, align, then proceed.**
Scope: model structure, signal direction / inversion logic, decision gates (decision_bucket), training pipeline, new feature sets, validation policy, data schema, signal-generation algorithm.
Format: filter through the three-role mental model and share an analysis covering:
1. **Quant view** — effect on win rate / return / drawdown, market-regime sensitivity, KOSPI vs KOSDAQ differences, 8:2 allocation impact, market hypothesis used or violated.
2. **Developer view** — affected modules, blast radius, staging vs big-bang, rollback procedure, regression risk, silent-fail risk (e.g. variant prefix mismatches).
3. **Validator view** — sample sufficiency, leakage risk, indicator consistency (val AUC vs CV median vs OOS), distribution shift between training and production.
4. **Sequence** — dependency order, what step to touch first.
5. **Structure** — how to modularize, validate, roll back.
6. **Gap** — what remains unsolved after this change.
7. **"Proceed?"**

**Meta layer — Claude proposes next goal, vision, direction.** The user decides. Just closing issues without tracing them to the 75%/15% target is treated as a failure mode ("intelligence-less mode").

### Forbidden patterns

- "다음에 뭐 할까요?" / sequencing handoff to the user.
- Producing tables, plans, or tier systems as a substitute for actually changing behavior.
- Closing strategic work without naming the gap to the 75%/15% target.
- Single-metric optimization (e.g. raw val AUC) without CV / OOS cross-checks.
- Treating model artifacts and code as independently deployable.
- Letting variant-prefix matches silently fail.

### Required patterns

- Lead with the gap. "Target 75%, observed 67%. Gap hypothesis: …."
- For strategic changes, share the role-based analysis before writing code.
- After every task, trace it back to the final goal and propose the next move.
- Treat Validator's stop as the strongest veto. No production signal without sample sufficiency, leakage check, and indicator consistency.

See also: `~/.claude/projects/.../memory/role_mental_model.md`, `feedback_communication_protocol.md`, `project_final_goal.md`.

---

## Collaboration with Codex

Codex is also an active collaborator in this repository. If you are Claude Code,
assume Codex may be editing nearby files in parallel during the same work
session.

- Shared discussion thread: `swing-main-0to`
  Use `bd comments swing-main-0to` to read context and
  `bd comment swing-main-0to "..."` to leave notes for Codex.
- Keep the thread high-signal only. Use it for file ownership warnings,
  blockers, proposed handoffs, and "I am about to touch this file" notices
  when the file is shared or conflict-prone.
- Do not emit routine START/END/PROGRESS comments for every normal task.
  Prefer issue status plus `bd close` for ordinary work tracking.
- If you do leave a collaboration note, prefix it with `[Claude]` or `[Codex]`
  because beads author names may not distinguish agents.
- Suggested handoff comment template:
  `STATUS: ...`
  `FILES: ...`
  `BLOCKERS: ...`
  `NEXT: ...`
- Treat existing unstaged or recently changed files as collaborator work unless
  you are sure they are yours.
- Coordinate work through `bd` first: run `bd prime`, inspect the issue, and
  claim it before editing.
- Before broad changes, check `git status --short` and keep your edit scope
  tight to the files owned by the claimed issue.
- Before conflict-prone work, acquire the merge slot with
  `bd merge-slot acquire`. Release it with `bd merge-slot release` after merge,
  branch-integration, or high-risk edits are done.
- If you touch a file that Codex may also be changing, prefer small targeted
  patches over full rewrites or sweeping reformatting.
- Never overwrite, revert, or normalize another agent's work just to make your
  change easier.
- If ownership is unclear or edits overlap, leave a short handoff note in `bd`
  and stop before creating a conflict.
- When finishing, close completed issues promptly with `bd close`.
- Only leave a thread handoff when another agent or the user would otherwise
  miss important context.

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


## Build & Test

_Add your build and test commands here_

```bash
# Example:
# npm install
# npm test
```

## Architecture Overview

_Add a brief overview of your project architecture_

## Conventions & Patterns

_Add your project-specific conventions here_
