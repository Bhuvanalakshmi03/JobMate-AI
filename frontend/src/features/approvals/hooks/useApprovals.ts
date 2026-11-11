import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { approvalService } from "../../../services/approval-service";
import type { ApprovalCreatePayload } from "../../../types/approval";

export function useApprovalsList(status?: string) {
  return useQuery({
    queryKey: ["approvals", "list", status ?? "all"],
    queryFn: () => approvalService.listApprovals(status || undefined),
    retry: false,
  });
}

export function useCreateApprovalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ApprovalCreatePayload) => approvalService.createApproval(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export function useApproveActionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { approvalId: string; note?: string | null }) =>
      approvalService.approve(params.approvalId, params.note),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export function useRejectActionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { approvalId: string; note?: string | null }) =>
      approvalService.reject(params.approvalId, params.note),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

