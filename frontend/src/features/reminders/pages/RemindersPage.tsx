import { BellRing, Check, Clock, Plus, RefreshCw, Trash2, XCircle } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  reminderStatusTone,
  type ReminderChannel,
  type ReminderType,
} from "../../../types/reminder";
import { useApplicationsList } from "../../applications/hooks/useApplications";
import { formatDisplayDate } from "../../applications/utils/dates";
import {
  useCancelReminderMutation,
  useCreateReminderMutation,
  useDeleteReminderMutation,
  useDismissReminderMutation,
  useDispatchRemindersMutation,
  useRemindersList,
} from "../hooks/useReminders";

function defaultReminderTimeLocal(): string {
  const dt = new Date(Date.now() + 2 * 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
}

export function RemindersPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const remindersQuery = useRemindersList(statusFilter);
  const applicationsQuery = useApplicationsList();

  const createMutation = useCreateReminderMutation();
  const cancelMutation = useCancelReminderMutation();
  const dismissMutation = useDismissReminderMutation();
  const dispatchMutation = useDispatchRemindersMutation();
  const deleteMutation = useDeleteReminderMutation();

  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [reminderType, setReminderType] = useState<ReminderType>("follow_up");
  const [applicationId, setApplicationId] = useState("");
  const [scheduledLocal, setScheduledLocal] = useState(defaultReminderTimeLocal);
  const [timezone, setTimezone] = useState(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  );
  const [channel, setChannel] = useState<ReminderChannel>("in_app");
  const [dedupKey, setDedupKey] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const items = remindersQuery.data?.items ?? [];
  const dueCount = remindersQuery.data?.due_notifications_count ?? 0;

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (title.trim().length < 2) {
      setFormError("Enter a reminder title.");
      return;
    }
    const parsed = new Date(scheduledLocal);
    if (Number.isNaN(parsed.getTime())) {
      setFormError("Enter a valid date and time.");
      return;
    }
    setFormError(null);
    try {
      await createMutation.mutateAsync({
        title: title.trim(),
        message: message.trim() || null,
        reminder_type: reminderType,
        application_id: applicationId || null,
        dedup_key: dedupKey.trim() || null,
        scheduled_for: parsed.toISOString(),
        timezone: timezone.trim() || "UTC",
        channel,
      });
      setTitle("");
      setMessage("");
      setDedupKey("");
    } catch {
      // Displayed via createMutation.error
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Reminders &amp; Notifications
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Timezone-aware application deadlines, recruiter follow-ups, and interview study checks
            with automatic deduplication and bounded retry delivery.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void dispatchMutation.mutateAsync()}
          disabled={dispatchMutation.isPending}
          className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3.5 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${dispatchMutation.isPending ? "animate-spin" : ""}`}
            aria-hidden="true"
          />
          {dispatchMutation.isPending ? "Checking Due..." : "Check Due Notifications"}
        </button>
      </header>

      {dispatchMutation.data && (
        <StateNotice
          title="Reminder sweep finished"
          description={`Processed ${dispatchMutation.data.processed} due reminder(s): ${dispatchMutation.data.sent} sent, ${dispatchMutation.data.retried_scheduled} queued for retry.`}
          tone="info"
        />
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <Card
            title="Schedule Reminder"
            subtitle="Stored in UTC and delivered cleanly without duplicate alerts."
          >
            <form onSubmit={(e) => void handleCreate(e)} className="space-y-3 text-xs">
              <div>
                <label htmlFor="rem-title" className="block font-medium text-slate-700">
                  Title
                </label>
                <input
                  id="rem-title"
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g., Follow up with Freshworks recruiter"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor="rem-type" className="block font-medium text-slate-700">
                    Type
                  </label>
                  <select
                    id="rem-type"
                    value={reminderType}
                    onChange={(e) => setReminderType(e.target.value as ReminderType)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm"
                  >
                    <option value="follow_up">Follow-Up</option>
                    <option value="deadline">Application Deadline</option>
                    <option value="interview">Interview Prep</option>
                    <option value="study_plan">Skill Study Plan</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="rem-channel" className="block font-medium text-slate-700">
                    Channel
                  </label>
                  <select
                    id="rem-channel"
                    value={channel}
                    onChange={(e) => setChannel(e.target.value as ReminderChannel)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm"
                  >
                    <option value="in_app">In-App Notification</option>
                    <option value="email_digest">Email Digest</option>
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor="rem-app" className="block font-medium text-slate-700">
                  Linked Application (optional)
                </label>
                <select
                  id="rem-app"
                  value={applicationId}
                  onChange={(e) => setApplicationId(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm"
                >
                  <option value="">None</option>
                  {(applicationsQuery.data?.items ?? []).map((app) => (
                    <option key={app.id} value={app.id}>
                      {app.role_title} — {app.company_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor="rem-when" className="block font-medium text-slate-700">
                    Scheduled Time
                  </label>
                  <input
                    id="rem-when"
                    type="datetime-local"
                    required
                    value={scheduledLocal}
                    onChange={(e) => setScheduledLocal(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="rem-tz" className="block font-medium text-slate-700">
                    Timezone (IANA)
                  </label>
                  <input
                    id="rem-tz"
                    type="text"
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    placeholder="Asia/Kolkata"
                    className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="rem-dedup" className="block font-medium text-slate-700">
                  Deduplication Key (optional)
                </label>
                <input
                  id="rem-dedup"
                  type="text"
                  value={dedupKey}
                  onChange={(e) => setDedupKey(e.target.value)}
                  placeholder="e.g., zoho-tech-followup"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label htmlFor="rem-msg" className="block font-medium text-slate-700">
                  Notes (optional)
                </label>
                <textarea
                  id="rem-msg"
                  rows={2}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Context for your follow-up or study session..."
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>

              {(formError || createMutation.error) && (
                <StateNotice
                  title="Unable to schedule reminder"
                  description={formError ?? createMutation.error?.message ?? "Invalid input."}
                  tone="error"
                />
              )}

              <button
                type="submit"
                disabled={createMutation.isPending}
                className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                {createMutation.isPending ? "Scheduling..." : "Schedule Reminder"}
              </button>
            </form>
          </Card>
        </div>

        <div className="lg:col-span-7">
          <Card
            title="Scheduled Reminders & Delivered Alerts"
            subtitle={`${items.length} reminder(s) · ${dueCount} active delivered alert(s)`}
            action={
              <select
                aria-label="Filter reminders by status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs"
              >
                <option value="">All Statuses</option>
                <option value="SCHEDULED">Scheduled</option>
                <option value="SENT">Delivered (Due)</option>
                <option value="FAILED">Failed / Retry</option>
                <option value="CANCELLED">Cancelled</option>
                <option value="DISMISSED">Dismissed</option>
              </select>
            }
          >
            {remindersQuery.isPending ? (
              <p className="text-xs text-slate-500">Loading reminders...</p>
            ) : remindersQuery.error ? (
              <StateNotice
                title="Unable to load reminders"
                description={remindersQuery.error.message}
                tone="error"
              />
            ) : items.length === 0 ? (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <BellRing className="h-4 w-4 text-indigo-500" aria-hidden="true" />
                <span>No reminders matching this filter.</span>
              </div>
            ) : (
              <ul className="space-y-2.5">
                {items.map((rem) => (
                  <li
                    key={rem.id}
                    className="rounded-lg border border-slate-200 bg-white p-3.5 text-xs"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{rem.title}</p>
                        {rem.message && <p className="mt-1 text-slate-600">{rem.message}</p>}
                      </div>
                      <StatusBadge label={rem.status} tone={reminderStatusTone(rem.status)} />
                    </div>

                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
                      <span className="inline-flex items-center gap-1 font-medium text-slate-700">
                        <Clock className="h-3 w-3 text-indigo-500" aria-hidden="true" />
                        {formatDisplayDate(rem.scheduled_for)} ({rem.user_timezone})
                      </span>
                      <span>Type: {rem.reminder_type}</span>
                      <span>Channel: {rem.channel}</span>
                      {rem.attempts > 0 && (
                        <span>
                          Attempts: {rem.attempts}/{rem.max_attempts}
                        </span>
                      )}
                    </div>

                    {rem.last_error && (
                      <p className="mt-1 text-[11px] text-rose-600">Last error: {rem.last_error}</p>
                    )}

                    <div className="mt-2.5 flex items-center justify-end gap-2">
                      {rem.status === "SENT" && (
                        <button
                          type="button"
                          onClick={() => void dismissMutation.mutateAsync(rem.id)}
                          className="inline-flex items-center gap-1 rounded border border-emerald-200 bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-700 hover:bg-emerald-100"
                        >
                          <Check className="h-3 w-3" /> Dismiss
                        </button>
                      )}
                      {(rem.status === "SCHEDULED" || rem.status === "FAILED") && (
                        <button
                          type="button"
                          onClick={() => void cancelMutation.mutateAsync(rem.id)}
                          className="inline-flex items-center gap-1 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-[11px] font-semibold text-amber-800 hover:bg-amber-100"
                        >
                          <XCircle className="h-3 w-3" /> Cancel
                        </button>
                      )}
                      <button
                        type="button"
                        aria-label={`Delete reminder ${rem.title}`}
                        onClick={() => void deleteMutation.mutateAsync(rem.id)}
                        className="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
