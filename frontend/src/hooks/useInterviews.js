// src/hooks/useInterviews.js
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "../api/client";

// ── Interviews ───────────────────────────────────────────────────────────────

export function useInterviews() {
  return useQuery({
    queryKey: ["interviews"],
    queryFn:  () => client.get("/api/v1/interviews").then((r) => r.data),
  });
}

export function useInterviewByJob(jobId) {
  return useQuery({
    queryKey: ["interviews", "job", jobId],
    queryFn:  () => client.get(`/api/v1/interviews/job/${jobId}`).then((r) => r.data),
    enabled:  !!jobId,
  });
}

export function useInterview(id) {
  return useQuery({
    queryKey: ["interviews", id],
    queryFn:  () => client.get(`/api/v1/interviews/${id}`).then((r) => r.data),
    enabled:  !!id,
  });
}

export function useCreateInterview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => client.post("/api/v1/interviews", data).then((r) => r.data),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ["interviews"] }),
  });
}

export function useUpdateInterview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) =>
      client.patch(`/api/v1/interviews/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interviews"] }),
  });
}

export function useDeleteInterview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => client.delete(`/api/v1/interviews/${id}`),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ["interviews"] }),
  });
}

// ── Questions CRUD ───────────────────────────────────────────────────────────

export function useCreateQuestion(interviewId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) =>
      client.post(`/api/v1/interviews/${interviewId}/questions`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interviews", interviewId] }),
  });
}

export function useUpdateQuestion(interviewId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ questionId, data }) =>
      client
        .patch(`/api/v1/interviews/${interviewId}/questions/${questionId}`, data)
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interviews", interviewId] }),
  });
}

export function useDeleteQuestion(interviewId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (questionId) =>
      client.delete(`/api/v1/interviews/${interviewId}/questions/${questionId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interviews", interviewId] }),
  });
}

// ── Questions AI ─────────────────────────────────────────────────────────────

export function useGenerateQuestions(interviewId) {
  const qc = useQueryClient();
  return useMutation({
    // POST /api/v1/interviews/{interviewId}/ai/generate-questions
    // payload: { title, company, interview_type, seniority_level, description, requirements, count }
    // returns: { questions: string[] }
    mutationFn: (payload) =>
      client
        .post(`/api/v1/interviews/${interviewId}/ai/generate-questions`, payload)
        .then((r) => r.data.questions),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interviews", interviewId] }),
  });
}

export function useEnhanceQuestion(interviewId) {
  return useMutation({
    mutationFn: ({ questionId, payload }) =>
      client
        .post(
          `/api/v1/interviews/${interviewId}/questions/${questionId}/ai/enhance`,
          payload
        )
        .then((r) => r.data.result),
  });
}

export function useGenerateRubric(interviewId) {
  return useMutation({
    mutationFn: ({ questionId, payload }) =>
      client.post(
        `/api/v1/interviews/${interviewId}/questions/${questionId}/ai/generate-rubric`,
        payload
      ).then((r) => r.data.result),
  });
}

export function useEnhanceRubric(interviewId) {
  return useMutation({
    mutationFn: ({ questionId, payload }) =>
      client.post(
        `/api/v1/interviews/${interviewId}/questions/${questionId}/ai/enhance-rubric`,
        payload
      ).then((r) => r.data.result),
  });
}

