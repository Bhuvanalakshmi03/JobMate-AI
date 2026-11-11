export type WorkflowTaskType = "auto" | "job_discovery" | "application_prep" | "career_advisory";

export interface TraceEntry {
  node: string;
  status: string;
  attempts: number;
  duration_ms: number;
  tokens_used: number;
  detail?: string | null;
  timestamp: string;
}

export interface WorkflowRun {
  id: string;
  user_id: string;
  job_id: string | null;
  application_id: string | null;
  task_type: string;
  user_request: string;
  current_stage: string;
  status: string;
  agent_outputs: Record<string, unknown>;
  validation_results: Record<string, unknown>;
  pending_approval_id: string | null;
  execution_trace: TraceEntry[];
  total_tokens_used: number;
  error_detail: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowListResponse {
  items: WorkflowRun[];
  total: number;
}

export interface WorkflowCreatePayload {
  requested_task: string;
  task_type?: WorkflowTaskType;
  job_id?: string | null;
  resume_id?: string | null;
  application_id?: string | null;
  search_query?: string | null;
  search_location?: string | null;
}

export interface RAGSyncResponse {
  indexed_chunks: number;
  skipped_duplicates: number;
  source_counts: Record<string, number>;
}

export interface RAGHit {
  chunk_id: string;
  score: number;
  source_type: string | null;
  label: string | null;
  text: string;
}

export interface RAGQueryResponse {
  query: string;
  hits: RAGHit[];
}

export function workflowStatusTone(
  status: string
): "success" | "warning" | "danger" | "info" | "neutral" {
  switch (status) {
    case "COMPLETED":
      return "success";
    case "PAUSED_FOR_APPROVAL":
      return "warning";
    case "FAILED":
      return "danger";
    case "RUNNING":
      return "info";
    default:
      return "neutral";
  }
}

