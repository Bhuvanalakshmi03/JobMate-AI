import { apiRequest } from "./api-client";
import type {
  ReminderCreatePayload,
  ReminderDispatchSummary,
  ReminderItem,
  ReminderListResponse,
} from "../types/reminder";

export const reminderService = {
  listReminders: (status?: string): Promise<ReminderListResponse> =>
    apiRequest<ReminderListResponse>(
      status ? `/reminders?status=${encodeURIComponent(status)}` : "/reminders"
    ),

  createReminder: (payload: ReminderCreatePayload): Promise<ReminderItem> =>
    apiRequest<ReminderItem>("/reminders", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  cancelReminder: (reminderId: string): Promise<ReminderItem> =>
    apiRequest<ReminderItem>(`/reminders/${reminderId}/cancel`, {
      method: "POST",
    }),

  dismissReminder: (reminderId: string): Promise<ReminderItem> =>
    apiRequest<ReminderItem>(`/reminders/${reminderId}/dismiss`, {
      method: "POST",
    }),

  dispatchDue: (): Promise<ReminderDispatchSummary> =>
    apiRequest<ReminderDispatchSummary>("/reminders/dispatch-due", {
      method: "POST",
    }),

  deleteReminder: (reminderId: string): Promise<void> =>
    apiRequest<void>(`/reminders/${reminderId}`, {
      method: "DELETE",
    }),
};
