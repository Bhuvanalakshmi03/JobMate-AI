import { apiRequest } from "./api-client";
import type {
  JobDetail,
  JobMatch,
  JobSearchParams,
  JobSearchResponse,
  RecommendedJobsResponse,
  SavedJobResponse,
} from "../types/job";

function buildSearchQueryString(params: JobSearchParams): string {
  const qs = new URLSearchParams();
  if (params.q?.trim()) qs.set("q", params.q.trim());
  if (params.location?.trim()) qs.set("location", params.location.trim());
  if (params.work_mode?.trim()) qs.set("work_mode", params.work_mode.trim());
  if (params.experience_level?.trim()) qs.set("experience_level", params.experience_level.trim());
  if (params.skills?.trim()) qs.set("skills", params.skills.trim());
  if (params.refresh) qs.set("refresh", "true");
  if (params.limit) qs.set("limit", String(params.limit));
  const rendered = qs.toString();
  return rendered ? `?${rendered}` : "";
}

export const jobService = {
  searchJobs: (params: JobSearchParams): Promise<JobSearchResponse> =>
    apiRequest<JobSearchResponse>(`/jobs/search${buildSearchQueryString(params)}`, {
      timeoutMs: 60000,
    }),

  getRecommended: (limit = 20): Promise<RecommendedJobsResponse> =>
    apiRequest<RecommendedJobsResponse>(`/jobs/recommended?limit=${limit}`, {
      timeoutMs: 45000,
    }),

  getSavedJobs: (): Promise<JobSearchResponse> => apiRequest<JobSearchResponse>("/jobs/saved"),

  getJobDetails: (jobId: string): Promise<JobDetail> => apiRequest<JobDetail>(`/jobs/${jobId}`),

  calculateMatch: (jobId: string): Promise<JobMatch> =>
    apiRequest<JobMatch>(`/jobs/${jobId}/match`, {
      method: "POST",
      timeoutMs: 30000,
    }),

  saveJob: (jobId: string, notes?: string): Promise<SavedJobResponse> =>
    apiRequest<SavedJobResponse>(`/jobs/${jobId}/save`, {
      method: "POST",
      body: JSON.stringify(notes ? { notes } : {}),
    }),

  unsaveJob: (jobId: string): Promise<void> =>
    apiRequest<void>(`/jobs/${jobId}/save`, {
      method: "DELETE",
    }),
};
