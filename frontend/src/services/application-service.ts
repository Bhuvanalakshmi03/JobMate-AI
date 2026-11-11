import { apiRequest } from "./api-client";
import type {
  ApplicationCreatePayload,
  ApplicationDetail,
  ApplicationListResponse,
  ApplicationStatus,
  ApplicationSummaryResponse,
  ApplicationTransitionPayload,
  ApplicationUpdatePayload,
} from "../types/application";

export interface ApplicationListParams {
  status?: ApplicationStatus | "";
  limit?: number;
  offset?: number;
}

export const applicationService = {
  listApplications: (params: ApplicationListParams = {}): Promise<ApplicationListResponse> => {
    const query = new URLSearchParams();
    if (params.status) query.set("status", params.status);
    if (params.limit !== undefined) query.set("limit", String(params.limit));
    if (params.offset !== undefined) query.set("offset", String(params.offset));
    const qs = query.toString();
    return apiRequest<ApplicationListResponse>(qs ? `/applications?${qs}` : "/applications");
  },

  getSummary: (): Promise<ApplicationSummaryResponse> =>
    apiRequest<ApplicationSummaryResponse>("/applications/summary"),

  createApplication: (payload: ApplicationCreatePayload): Promise<ApplicationDetail> =>
    apiRequest<ApplicationDetail>("/applications", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getApplication: (applicationId: string): Promise<ApplicationDetail> =>
    apiRequest<ApplicationDetail>(`/applications/${applicationId}`),

  updateApplication: (
    applicationId: string,
    payload: ApplicationUpdatePayload
  ): Promise<ApplicationDetail> =>
    apiRequest<ApplicationDetail>(`/applications/${applicationId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  transitionApplication: (
    applicationId: string,
    payload: ApplicationTransitionPayload
  ): Promise<ApplicationDetail> =>
    apiRequest<ApplicationDetail>(`/applications/${applicationId}/transition`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deleteApplication: (applicationId: string): Promise<void> =>
    apiRequest<void>(`/applications/${applicationId}`, {
      method: "DELETE",
    }),
};
