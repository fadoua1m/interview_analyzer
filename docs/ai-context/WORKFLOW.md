# Context Workflow

## When to Update
Update context files when you:
- change output contracts,
- modify scoring logic,
- add/remove endpoints,
- change user-visible HR wording,
- close/open significant tasks.

## Minimal Update Checklist
1. `ACTIVE_CONTEXT.md`
   - what changed
   - next actions
2. `DECISIONS_LOG.md`
   - append 1-3 bullets with date
3. `HANDOFF.md`
   - overwrite with latest session handoff

## Authoring Rules
- Keep language concise and factual.
- Prefer stable facts over temporary debugging notes.
- Use plain Markdown only.
- Do not duplicate long code snippets.

## Suggested Cadence
- During active development: update once per meaningful task.
- End of session: always refresh `HANDOFF.md`.

## Optional Automation (Future)
- Add a pre-PR checklist item: "AI context docs updated".
- Add CI markdown lint for `docs/ai-context/*.md`.
