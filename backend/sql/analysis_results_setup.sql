-- Ensure analysis_results has recruiter-report columns used by backend payload
-- Run in Supabase SQL editor

CREATE TABLE IF NOT EXISTS public.analysis_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  interview_id uuid NOT NULL,
  hr_view jsonb,
  overall_score numeric,
  decision text,
  decision_reasons text[],
  hr_summary text,
  generated_at timestamptz DEFAULT now(),
  qa_pairs_count integer DEFAULT 0,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE public.analysis_results
  ADD COLUMN IF NOT EXISTS hr_view jsonb,
  ADD COLUMN IF NOT EXISTS overall_score numeric,
  ADD COLUMN IF NOT EXISTS decision text,
  ADD COLUMN IF NOT EXISTS decision_reasons text[],
  ADD COLUMN IF NOT EXISTS hr_summary text,
  ADD COLUMN IF NOT EXISTS generated_at timestamptz,
  ADD COLUMN IF NOT EXISTS qa_pairs_count integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();

-- Upsert in backend uses on_conflict=interview_id
CREATE UNIQUE INDEX IF NOT EXISTS analysis_results_interview_id_uidx
  ON public.analysis_results (interview_id);
