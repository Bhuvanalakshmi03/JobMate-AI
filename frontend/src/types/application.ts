export type ApplicationStatus =
  | "SAVED"
  | "PREPARING"
  | "AWAITING_APPROVAL"
  | "SUBMITTED"
  | "INTERVIEW_SCHEDULED"
  | "REJECTED"
  | "OFFER_RECEIVED"
  | "WITHDRAWN";

export const APPLICATION_STATUS_ORDER: ApplicationStatus[] = [
  "SAVED",
  "PREPARING",
  "AWAITING_APPROVAL",
  "SUBMITTED",
  "INTERVIEW_SCHEDULED",
  "OFFER_RECEIVED",
  "REJECTED",
  "WITHDRAWN",
];

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  SAVED: "Saved",
  PREPARING: "Preparing",
  AWAITING_APPROVAL: "Awaiting Approval",
  SUBMITTED: "Submitted",
  INTERVIEW_SCHEDULED: "Interview Scheduled",
  OFFER_RECEIVED: "Offer Received",
  REJECTED: "Rejected",
  WITHDRAWN: "Withdrawn",
};

export function applicationStatusLabel(status: string): string {
  return APPLICATION_STATUS_LABELS[status as ApplicationStatus] ?? status.replaceAll("_", " ");
}

export function applicationStatusTone(
  status: string
): "success" | "warning" | "danger" | "info" | "neutral" {
  switch (status) {
    case "OFFER_RECEIVED":
    case "SUBMITTED":
      return "success";
    case "INTERVIEW_SCHEDULED":
    case "PREPARING":
      return "info";
    case "AWAITING_APPROVAL":
      return "warning";
    case "REJECTED":
      return "danger";
    default:
      return "neutral";
  }
}

export interface ApplicationHistoryItem {
  id: string;
  from_status: string | null;
  to_status: string;
  note: string | null;
  changed_at: string;
}

export interface ApplicationItem {
  id: string;
  user_id: string;
  job_id: string | null;
  tailored_resume_id: string | null;
  cover_letter_id: string | null;
  company_name: string;
  role_title: string;
  job_url: string | null;
  location: string | null;
  status: ApplicationStatus;
  allowed_next_statuses: ApplicationStatus[];
  applied_at: string | null;
  deadline_at: string | null;
  follow_up_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationDetail extends ApplicationItem {
  history: ApplicationHistoryItem[];
}

export interface ApplicationListResponse {
  items: ApplicationItem[];
  total: number;
}

export interface ApplicationSummaryResponse {
  total_applications: number;
  counts_by_status: Record<string, number>;
  upcoming_deadlines: ApplicationItem[];
}

export interface ApplicationCreatePayload {
  job_id?: string | null;
  company_name?: string | null;
  role_title?: string | null;
  job_url?: string | null;
  location?: string | null;
  tailored_resume_id?: string | null;
  cover_letter_id?: string | null;
  deadline_at?: string | null;
  follow_up_at?: string | null;
  notes?: string | null;
}

export interface ApplicationUpdatePayload {
  company_name?: string | null;
  role_title?: string | null;
  job_url?: string | null;
  location?: string | null;
  tailored_resume_id?: string | null;
  cover_letter_id?: string | null;
  deadline_at?: string | null;
  follow_up_at?: string | null;
  notes?: string | null;
}

export interface ApplicationTransitionPayload {
  target_status: ApplicationStatus;
  note?: string | null;
}
