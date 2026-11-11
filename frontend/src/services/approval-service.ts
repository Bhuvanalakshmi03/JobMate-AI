import { apiRequest } from "./api-client";
import type {
  ApprovalCreatePayload,
  ApprovalItem,
  ApprovalListResponse,
} from "../types/approval";

export const approvalService = {
  listApprovals: (status?: string): Promise<ApprovalListResponse> =>
    apiRequest<ApprovalListResponse>(
      status ? `/approvals?status=${encodeURIComponent(status)}` : "/approvals"
    ),

  createApproval: (payload: ApprovalCreatePayload): Promise<ApprovalItem> =>
    apiRequest<ApprovalItem>("/approvals", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getApproval: (approvalId: string): Promise<ApprovalItem> =>
    apiRequest<ApprovalItem>(`/approvals/${approvalId}`),

  approve: (approvalId: string, note?: string | null): Promise<ApprovalItem> =>
    apiRequest<ApprovalItem>(`/approvals/${approvalId}/approve`, {
      method: "POST",
      body: JSON.stringify({ note: note ?? null }),
    }),

  reject: (approvalId: string, note?: string | null): Promise<ApprovalItem> =>
    apiRequest<ApprovalItem>(`/approvals/${approvalId}/reject`, {
      method: "POST",
      body: JSON.stringify({ note: note ?? null }),
    }),
};

