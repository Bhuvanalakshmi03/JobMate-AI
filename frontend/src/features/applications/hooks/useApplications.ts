import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  applicationService,
  type ApplicationListParams,
} from "../../../services/application-service";
import type {
  ApplicationCreatePayload,
  ApplicationTransitionPayload,
  ApplicationUpdatePayload,
} from "../../../types/application";

export function useApplicationsList(params: ApplicationListParams = {}) {
  return useQuery({
    queryKey: ["applications", "list", params],
    queryFn: () => applicationService.listApplications(params),
    retry: false,
  });
}

export function useApplicationSummary(enabled = true) {
  return useQuery({
    queryKey: ["applications", "summary"],
    queryFn: () => applicationService.getSummary(),
    enabled,
    retry: false,
  });
}

export function useApplicationDetail(applicationId: string) {
  return useQuery({
    queryKey: ["applications", "detail", applicationId],
    queryFn: () => applicationService.getApplication(applicationId),
    enabled: Boolean(applicationId),
    retry: false,
  });
}

export function useCreateApplicationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ApplicationCreatePayload) =>
      applicationService.createApplication(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export function useUpdateApplicationMutation(applicationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ApplicationUpdatePayload) =>
      applicationService.updateApplication(applicationId, payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["applications", "detail", applicationId], updated);
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export function useTransitionApplicationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { applicationId: string } & ApplicationTransitionPayload) =>
      applicationService.transitionApplication(params.applicationId, {
        target_status: params.target_status,
        note: params.note,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["applications", "detail", updated.id], updated);
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export function useDeleteApplicationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (applicationId: string) => applicationService.deleteApplication(applicationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}
