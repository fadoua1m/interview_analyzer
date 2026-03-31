# Decisions Log

Use newest-first entries.

## 2026-03-27
- Public API responses for analysis endpoints were standardized to a slim HR payload (`PublicAnalysisResponse`) to remove redundancy.
- `text_profile` now includes `softskills` evidence items with fields: `name`, `strength`, `quote`, `reason`.
- `decision_reasons` were constrained and normalized to short HR-friendly phrasing.

## 2026-03-25
- Added recruiter-facing `hr_view` with `video_profile`, `audio_profile`, and `text_profile`.
- Rewrote key observations in plain HR language across audio/video/text.
- Added bilingual EN/FR handling in parts of audio scoring.
- Removed non-deterministic accuracy branch from audio path.
