# Session Handoff

_Last updated: 2026-03-27_

## Completed in This Session
- Implemented persistent Markdown context system under `docs/ai-context/`.
- Documented architecture, decisions, live state, and maintenance workflow.

## Current Code Expectations
- Analysis endpoints should return only:
  - `interview_id`
  - `hr_view`
  - `overall_score`
  - `decision`
  - `decision_reasons`
  - `hr_summary`
- `hr_view.text_profile.softskills` should include extracted evidence entries.

## Recommended First Check in Next Session
- Run one real analysis request and verify output keys exactly match public contract.
- Confirm `decision_reasons` are short and HR-friendly.

## If Something Looks Wrong
- Inspect `backend/app/routes/analysis.py` response model + payload builders.
- Inspect `backend/app/analysis_pipeline/report_assembler.py` for reason generation and text profile composition.
