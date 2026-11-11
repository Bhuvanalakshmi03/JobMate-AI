import { apiRequest } from "./api-client";
import type {
  RAGQueryResponse,
  RAGSyncResponse,
  WorkflowCreatePayload,
  WorkflowListResponse,
  WorkflowRun,
} from "../types/agent";

export const agentService = {
  startWorkflow: (payload: WorkflowCreatePayload): Promise<WorkflowRun> =>
    apiRequest<WorkflowRun>("/agents/workflows", {
      method: "POST",
      timeoutMs: 60000,
      body: JSON.stringify(payload),
    }),

  listWorkflows: (): Promise<WorkflowListResponse> =>
    apiRequest<WorkflowListResponse>("/agents/workflows"),

  getWorkflow: (workflowId: string): Promise<WorkflowRun> =>
    apiRequest<WorkflowRun>(`/agents/workflows/${workflowId}`),

  syncRag: (): Promise<RAGSyncResponse> =>
    apiRequest<RAGSyncResponse>("/agents/rag/sync", {
      method: "POST",
      timeoutMs: 45000,
    }),

  queryRag: (params: { query: string; top_k?: number }): Promise<RAGQueryResponse> =>
    apiRequest<RAGQueryResponse>("/agents/rag/query", {
      method: "POST",
      body: JSON.stringify(params),
    }),
};

