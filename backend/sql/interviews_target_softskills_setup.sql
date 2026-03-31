-- Add recruiter target soft skills to interviews if missing
-- Run this in Supabase SQL editor

ALTER TABLE public.interviews
ADD COLUMN IF NOT EXISTS target_softskills text[];

UPDATE public.interviews
SET target_softskills = '{}'::text[]
WHERE target_softskills IS NULL;

ALTER TABLE public.interviews
ALTER COLUMN target_softskills SET DEFAULT '{}'::text[];

ALTER TABLE public.interviews
ALTER COLUMN target_softskills SET NOT NULL;
