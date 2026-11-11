export type ReminderType = "deadline" | "follow_up" | "interview" | "study_plan" | "custom";
export type ReminderChannel = "in_app" | "email_digest";

export interface ReminderItem {
  id: string;
  user_id: string;
  application_id: string | null;
  job_id: string | null;
  title: string;
  message: string | null;
  reminder_type: string;
  dedup_key: string | null;
  scheduled_for: string;
  user_timezone: string;
  channel: string;
  status: string;
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  sent_at: string | null;
  next_retry_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReminderListResponse {
  items: ReminderItem[];
  total: number;
  due_notifications_count: number;
}

export interface ReminderCreatePayload {
  title: string;
  message?: string | null;
  reminder_type: ReminderType;
  application_id?: string | null;
  dedup_key?: string | null;
  scheduled_for: string;
  timezone?: string | null;
  channel?: ReminderChannel;
}

export interface ReminderDispatchSummary {
  processed: number;
  sent: number;
  failed: number;
  retried_scheduled: number;
}

export function reminderStatusTone(
  status: string
): "success" | "warning" | "danger" | "info" | "neutral" {
  switch (status) {
    case "SENT":
      return "success";
    case "SCHEDULED":
      return "info";
    case "FAILED":
      return "danger";
    case "CANCELLED":
    case "DISMISSED":
      return "neutral";
    default:
      return "warning";
  }
}
