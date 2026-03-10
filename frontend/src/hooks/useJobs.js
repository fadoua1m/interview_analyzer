import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "../api/client";

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn:  () => client.get("/api/v1/jobs").then((r) => r.data),
  });
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => client.post("/api/v1/jobs", data).then((r) => r.data),
    onSuccess:  () => queryClient.invalidateQueries(["jobs"]),
  });
}

export function useUpdateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) =>
      client.patch(`/api/v1/jobs/${id}`, data).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries(["jobs"]),
  });
}

export function useDeleteJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => client.delete(`/api/v1/jobs/${id}`),
    onSuccess:  () => queryClient.invalidateQueries(["jobs"]),
  });
}