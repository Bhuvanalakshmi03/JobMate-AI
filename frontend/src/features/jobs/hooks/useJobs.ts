import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { jobService } from "../../../services/job-service";
import type { JobSearchParams } from "../../../types/job";

export function useJobSearch(params: JobSearchParams, enabled = true) {
  return useQuery({
    queryKey: ["jobs", "search", params],
    queryFn: () => jobService.searchJobs(params),
    enabled,
    retry: false,
  });
}

export function useRecommendedJobs(enabled = true) {
  return useQuery({
    queryKey: ["jobs", "recommended"],
    queryFn: () => jobService.getRecommended(20),
    enabled,
    retry: false,
  });
}

export function useSavedJobs(enabled = true) {
  return useQuery({
    queryKey: ["jobs", "saved"],
    queryFn: jobService.getSavedJobs,
    enabled,
    retry: false,
  });
}

export function useJobDetail(jobId: string) {
  return useQuery({
    queryKey: ["jobs", "detail", jobId],
    queryFn: () => jobService.getJobDetails(jobId),
    enabled: Boolean(jobId),
    retry: false,
  });
}

export function useCalculateJobMatchMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => jobService.calculateMatch(jobId),
    onSuccess: (_data, jobId) => {
      void queryClient.invalidateQueries({ queryKey: ["jobs", "detail", jobId] });
      void queryClient.invalidateQueries({ queryKey: ["jobs", "search"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs", "recommended"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs", "saved"] });
    },
  });
}

export function useToggleSaveJobMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ jobId, isSaved }: { jobId: string; isSaved: boolean }): Promise<void> => {
      if (isSaved) {
        await jobService.unsaveJob(jobId);
      } else {
        await jobService.saveJob(jobId);
      }
    },
    onSuccess: (_data, { jobId }) => {
      void queryClient.invalidateQueries({ queryKey: ["jobs", "detail", jobId] });
      void queryClient.invalidateQueries({ queryKey: ["jobs", "search"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs", "recommended"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs", "saved"] });
    },
  });
}
