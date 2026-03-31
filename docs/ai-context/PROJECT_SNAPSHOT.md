# Project Snapshot

_Last updated: 2026-03-27_

## Product
AI Interview Analyzer with recruiter-facing output (`hr_view`) generated from:
- video behavior signals,
- audio delivery signals,
- text relevance + soft skills evidence.

## Current Output Contract (Public)
Expected public response shape:
- `interview_id`
- `hr_view`
  - `video_profile`
  - `audio_profile`
  - `text_profile`
    - `softskills` (`name`, `strength`, `quote`, `reason`)
  - `video_reliable`
  - `audio_reliable`
- `overall_score`
- `decision`
- `decision_reasons` (short, HR-friendly)
- `hr_summary`

## Current State
- HR-friendly profiles are implemented (`audio_profile`, `video_profile`, `text_profile`).
- Redundant raw fields are removed from public analysis endpoints.
- `decision_reasons` are normalized to short HR language.
- Soft skills evidence is included inside `text_profile.softskills`.

## Known Constraints
- Keep recruiter response plain-language (no technical jargon).
- Keep deterministic/rules-based behavior where possible.
- Preserve internal raw metrics for diagnostics, but do not expose publicly.
