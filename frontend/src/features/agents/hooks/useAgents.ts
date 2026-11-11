import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { agentService } from "../../../services/agent-service";
import type { WorkflowCreatePayload } from "../../../types/agent";

export function useWorkflowsList() {
  return useQuery({
    queryKey: ["agents", "workflows"],
    queryFn: agentService.listWorkflows,
    retry: false,
  });
}

export function useWorkflowDetail(workflowId: string) {
  return useQuery({
    queryKey: ["agents", "workflow", workflowId],
    queryFn: () => agentService.getWorkflow(workflowId),
    enabled: Boolean(workflowId),
    retry: false,
  });
}

export function useStartWorkflowMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: WorkflowCreatePayload) => agentService.startWorkflow(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
      void queryClient.invalidateQueries({ queryKey: ["approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useSyncRagMutation() {
  return useMutation({
    mutationFn: agentService.syncRag,
  });
}

export function useQueryRagMutation() {
  return useMutation({
    mutationFn: (params: { query: string; top_k?: number }) => agentService.queryRag(params),
  });
}

