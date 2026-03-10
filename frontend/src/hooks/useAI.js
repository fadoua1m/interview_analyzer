/**
 * src/hooks/useAI.js
 * Hooks for all Gemini AI enhancement features.
 */
import { useMutation } from "@tanstack/react-query";
import client from "../api/client";

export function useEnhanceDescription() {
  return useMutation({
    mutationFn: ({ title, company, description }) =>
      client
        .post("/api/v1/ai/enhance-description", { title, company, description })
        .then((r) => r.data.result),
  });
}

export function useGenerateRequirements() {
  return useMutation({
    mutationFn: ({ title, company, description }) =>
      client
        .post("/api/v1/ai/generate-requirements", { title, company, description })
        .then((r) => r.data.result),
  });
}

export function useEnhanceRequirements() {
  return useMutation({
    mutationFn: ({ title, requirements }) =>
      client
        .post("/api/v1/ai/enhance-requirements", { title, requirements })
        .then((r) => r.data.result),
  });
}