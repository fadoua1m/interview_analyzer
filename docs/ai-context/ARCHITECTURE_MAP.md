# Architecture Map

_Last updated: 2026-03-27_

## Backend (`backend/app`)
- `routes/analysis.py`
  - `/analysis/run`
  - `/analysis/run-upload`
  - `/analysis/{interview_id}`
  - Returns `PublicAnalysisResponse` (slim HR payload)
- `analysis_pipeline/pipeline.py`
  - orchestration entry point for full analysis
- `analysis_pipeline/report_assembler.py`
  - normalizes modality outputs
  - computes overall score
  - builds `hr_view`
  - generates decision + reasons + summary
- `analysis_pipeline/text/soft_skills_module.py`
  - extracts soft skill evidence from transcript/QA
- `routes/softskills.py`
  - CRUD API for bilingual softskills bank stored in Supabase
- `services/softskills_bank.py`
  - DB access + validation for active softskill keys
- `schemas/analysis.py`
  - Pydantic contracts for internal + public payloads

## Frontend (`frontend/src`)
- consumes analysis APIs
- recruiter UI should rely on `hr_view` + overall decision fields

## Data Flow (High-Level)
1. Interview input (`video_url` or upload + questions)
2. Pipeline extracts transcript/audio/video features
3. Recruiter-managed softskills bank (EN/FR) is loaded from DB
4. Interview target softskills are merged with question targets
5. Text relevance + soft skills are scored/extracted against DB competency definitions
4. Report assembler builds `CandidateReport` internally
5. Route converts to public slim payload and stores/returns it

## Softskills Workflow (Canonical)
1. Recruiter creates interview questions.
2. Recruiter optionally creates/edits rubric per question.
3. Recruiter selects interview-level target softskills from bank.
4. Candidate submits video.
5. Text module verifies requested skills as found/missing with strength evidence.
6. Requested-skill match affects overall score.

## Public vs Internal Separation
- Internal: full raw diagnostics and intermediate metrics
- Public: recruiter-focused output only (`PublicAnalysisResponse`)
