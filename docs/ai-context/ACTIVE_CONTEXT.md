# Active Context

_Last updated: 2026-03-27_

## Current Objective
Maintain recruiter-safe response quality and keep API output minimal and non-redundant.

## What Was Just Completed
- Slim API response enforced on analysis routes.
- Soft skill evidence moved into `hr_view.text_profile.softskills`.
- Decision reasons shortened for HR readability.
- Competency definitions moved from code constants to Supabase softskills bank.
- Added softskills CRUD API + frontend bank management page.
- Enforced workflow: questions/rubrics first, then interview target softskills selection.

## Open Follow-ups
- Verify frontend screens consume only the slim payload (no dependency on removed raw fields).
- Standardize categorical labels across profiles (optional hardening).
- Add integration tests for response shape contract.
- Add end-to-end test for requested softskills found/missing + score impact.

## Risks / Watchouts
- Legacy rows in storage may still contain old shape; route normalizer handles this at read time.
- Any new endpoint must use `PublicAnalysisResponse` for consistency.

## Next Actions
1. Add contract tests for `/analysis/run` and `/analysis/{interview_id}`.
2. Update frontend hooks/types if they still read old fields.
3. Add one golden sample JSON fixture for regression checks.
4. Apply `backend/sql/softskills_bank_setup.sql` in Supabase and add French entries.
