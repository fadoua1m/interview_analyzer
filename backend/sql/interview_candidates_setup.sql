create table if not exists public.interview_candidates (
  id uuid primary key default gen_random_uuid(),
  interview_id uuid not null references public.interviews(id) on delete cascade,
  name text not null,
  email text not null,
  status text not null default 'assigned',
  access_token text not null unique,
  submitted_at timestamptz null,
  analysis_payload jsonb null,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create unique index if not exists interview_candidates_interview_email_unique
  on public.interview_candidates(interview_id, lower(email));

create index if not exists interview_candidates_interview_idx
  on public.interview_candidates(interview_id);

create index if not exists interview_candidates_token_idx
  on public.interview_candidates(access_token);
