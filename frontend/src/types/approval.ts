export type ApprovalActionType =
  | "submit_application"
  | "send_recruiter_email"
  | "upload_external_resume"
  | "send_application_message";

export type ApprovalStatus =
  | "PENDING"
  | "APPROVED"
  | "REJECTED"
  | "EXECUTED"
  | "FAILED"
  | "CANCELLED";

export interface ApprovalItem {
  id: string;
  user_id: string;
  workflow_run_id: string | null;
  application_id: string | null;
  action_type: ApprovalActionType | string;
  target_destination: string;
  title: string;
  payload: Record<string, unknown>;
  status: ApprovalStatus | string;
  decision_note: string | null;
  decided_at: string | null;
  executed_at: string | null;
  execution_result: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ApprovalListResponse {
  items: ApprovalItem[];
  total: number;
  pending_count: number;
}

export interface ApprovalCreatePayload {
  action_type: ApprovalActionType;
  application_id?: string | null;
  target_destination: string;
  title: string;
  payload?: Record<string, unknown>;
}

export function approvalStatusTone(
  status: string
): "success" | "warning" | "danger" | "info" | "neutral" {
  switch (status) {
    case "EXECUTED":
    case "APPROVED":
      return "success";
    case "PENDING":
      return "warning";
    case "REJECTED":
    case "FAILED":
      return "danger";
    default:
      return "neutral";
  }
}

export function approvalActionLabel(actionType: string): string {
  switch (actionType) {
    case "submit_application":
      return "Submit Application";
    case "send_recruiter_email":
      return "Send Recruiter Email";
    case "upload_external_resume":
      return "Upload External Resume";
    case "send_application_message":
      return "Send Application Message";
    default:
      return actionType.replaceAll("_", " ");
  }
}

