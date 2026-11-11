import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { resumeService } from "../../../services/resume-service";
import type { FactPatchItem } from "../../../types/resume";

export function useResumesList() {
  return useQuery({
    queryKey: ["resumes", "list"],
    queryFn: resumeService.listResumes,
    retry: false,
  });
}

export function useResumeAnalysis(resumeId: string) {
  return useQuery({
    queryKey: ["resumes", "analysis", resumeId],
    queryFn: () => resumeService.getAnalysis(resumeId),
    enabled: Boolean(resumeId),
    retry: false,
  });
}

export function useUploadResumeMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => resumeService.uploadResume(file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["resumes", "list"] });
    },
  });
}

export function useAnalyzeResumeMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ resumeId, force = false }: { resumeId: string; force?: boolean }) =>
      resumeService.analyzeResume(resumeId, force),
    onSuccess: (data) => {
      queryClient.setQueryData(["resumes", "analysis", data.resume.id], data);
      void queryClient.invalidateQueries({ queryKey: ["resumes", "list"] });
    },
  });
}

export function usePatchFactsMutation(resumeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      updates,
      syncToProfile = true,
    }: {
      updates: FactPatchItem[];
      syncToProfile?: boolean;
    }) => resumeService.patchFacts(resumeId, updates, syncToProfile),
    onSuccess: (_res, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["resumes", "analysis", resumeId] });
      if (variables.syncToProfile) {
        void queryClient.invalidateQueries({ queryKey: ["profile"] });
      }
    },
  });
}

export function useDeleteResumeMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (resumeId: string) => resumeService.deleteResume(resumeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["resumes", "list"] });
    },
  });
}
