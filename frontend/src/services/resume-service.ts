import { apiRequest } from "./api-client";
import type {
  FactPatchItem,
  ResumeAnalysisResponse,
  ResumeFactsPatchResponse,
  ResumeListResponse,
  ResumeSummary,
} from "../types/resume";

export const resumeService = {
  uploadResume: (file: File): Promise<ResumeSummary> => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest<ResumeSummary>("/resumes/upload", {
      method: "POST",
      body: formData,
    });
  },

  listResumes: (): Promise<ResumeListResponse> => apiRequest<ResumeListResponse>("/resumes"),

  analyzeResume: (resumeId: string, force = false): Promise<ResumeAnalysisResponse> =>
    apiRequest<ResumeAnalysisResponse>(
      `/resumes/${resumeId}/analyze${force ? "?force=true" : ""}`,
      {
        method: "POST",
        timeoutMs: 60000,
      }
    ),

  getAnalysis: (resumeId: string): Promise<ResumeAnalysisResponse> =>
    apiRequest<ResumeAnalysisResponse>(`/resumes/${resumeId}/analysis`),

  patchFacts: (
    resumeId: string,
    updates: FactPatchItem[],
    syncToProfile = true
  ): Promise<ResumeFactsPatchResponse> =>
    apiRequest<ResumeFactsPatchResponse>(`/resumes/${resumeId}/facts`, {
      method: "PATCH",
      body: JSON.stringify({ updates, sync_to_profile: syncToProfile }),
    }),

  deleteResume: (resumeId: string): Promise<void> =>
    apiRequest<void>(`/resumes/${resumeId}`, {
      method: "DELETE",
    }),
};
