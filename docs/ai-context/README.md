# AI Context System (Persistent)

This folder is the **single source of truth** for persistent AI context in this project.

Use it to preserve technical decisions, current status, and handoff notes across sessions.

## Goals
- Keep context stable across chat resets.
- Avoid re-discovery of architecture and past decisions.
- Speed up onboarding for new contributors or AI sessions.
- Keep HR-facing output requirements explicit and traceable.

## File Map
- `PROJECT_SNAPSHOT.md` — current product scope, stack, and constraints.
- `ARCHITECTURE_MAP.md` — backend/frontend flow and key modules.
- `DECISIONS_LOG.md` — decision history with rationale and impact.
- `ACTIVE_CONTEXT.md` — in-progress tasks, blockers, next actions.
- `HANDOFF.md` — structured session handoff for continuity.
- `WORKFLOW.md` — maintenance workflow for this context system.

## Update Workflow (Required)
1. Before starting work:
   - Read `PROJECT_SNAPSHOT.md`, `DECISIONS_LOG.md`, and `ACTIVE_CONTEXT.md`.
2. During work:
   - Append key decisions to `DECISIONS_LOG.md`.
   - Update status and TODOs in `ACTIVE_CONTEXT.md`.
3. Before ending a session:
   - Refresh `HANDOFF.md`.

## Writing Rules
- Keep entries factual and short.
- Write dates in `YYYY-MM-DD`.
- For each decision include: **Context / Decision / Impact**.
- Prefer links to code locations over long code snippets.
- Do not store secrets, credentials, tokens, or personal data.
