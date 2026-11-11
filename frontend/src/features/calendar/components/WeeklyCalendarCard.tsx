import {
  Calendar,
  CalendarClock,
  CalendarPlus,
  Clock,
  ExternalLink,
  MapPin,
  RefreshCw,
  Unlink,
} from "lucide-react";
import { useState, type FormEvent } from "react";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import type { CalendarEventItem } from "../../../types/calendar";
import {
  useApprovalsList,
  useApproveActionMutation,
  useRejectActionMutation,
} from "../../approvals/hooks/useApprovals";
import {
  useCalendarEvents,
  useCalendarStatus,
  useConnectCalendarMutation,
  useCreateCalendarEventMutation,
  useDisconnectCalendarMutation,
} from "../hooks/useCalendar";

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

interface WeeklyCalendarCardProps {
  compact?: boolean;
  redirectTo?: string;
}

function parseEventDate(rawIso: string, isEndBoundary = false): number | null {
  const trimmed = rawIso.trim();
  if (!trimmed) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    const base = new Date(`${trimmed}T00:00:00`);
    if (Number.isNaN(base.getTime())) return null;
    return isEndBoundary ? base.getTime() : base.getTime();
  }
  const parsed = new Date(trimmed);
  return Number.isNaN(parsed.getTime()) ? null : parsed.getTime();
}

function isAllDayIso(rawIso: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(rawIso.trim());
}

function formatDayGroupHeader(startIso: string, now: Date): string {
  const trimmed = startIso.trim();
  const dateObj = /^\d{4}-\d{2}-\d{2}$/.test(trimmed)
    ? new Date(`${trimmed}T00:00:00`)
    : new Date(trimmed);
  if (Number.isNaN(dateObj.getTime())) return "Scheduled";

  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const itemStart = new Date(
    dateObj.getFullYear(),
    dateObj.getMonth(),
    dateObj.getDate()
  ).getTime();
  const diffDays = Math.round((itemStart - todayStart) / (24 * 60 * 60 * 1000));

  const label = dateObj.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  if (diffDays === 0) return `Today · ${label}`;
  if (diffDays === 1) return `Tomorrow · ${label}`;
  return label;
}

function formatTimeRange(startIso: string, endIso: string): string {
  if (isAllDayIso(startIso)) {
    return "All day";
  }
  const start = new Date(startIso);
  const end = new Date(endIso);
  if (Number.isNaN(start.getTime())) return startIso;

  const startStr = start.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
  if (Number.isNaN(end.getTime())) return startStr;

  const endStr = end.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
  return `${startStr} – ${endStr}`;
}

function groupEventsByDay(events: CalendarEventItem[], now: Date): Array<{
  dayKey: string;
  dayLabel: string;
  items: CalendarEventItem[];
}> {
  const nowMs = now.getTime();
  const weekEndMs = nowMs + SEVEN_DAYS_MS;

  const withinWeek = events
    .filter((evt) => {
      const startMs = parseEventDate(evt.start_iso);
      const endMs = parseEventDate(evt.end_iso, true) ?? startMs;
      if (startMs === null) return true;
      return startMs < weekEndMs && (endMs === null || endMs >= nowMs);
    })
    .sort((a, b) => a.start_iso.localeCompare(b.start_iso));

  const groups = new Map<string, { dayLabel: string; items: CalendarEventItem[] }>();
  for (const evt of withinWeek) {
    const trimmed = evt.start_iso.trim();
    const d = /^\d{4}-\d{2}-\d{2}$/.test(trimmed)
      ? new Date(`${trimmed}T00:00:00`)
      : new Date(trimmed);
    const dayKey = Number.isNaN(d.getTime())
      ? evt.start_iso
      : `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const existing = groups.get(dayKey);
    if (existing) {
      existing.items.push(evt);
    } else {
      groups.set(dayKey, {
        dayLabel: formatDayGroupHeader(evt.start_iso, now),
        items: [evt],
      });
    }
  }

  return Array.from(groups.entries()).map(([dayKey, value]) => ({
    dayKey,
    dayLabel: value.dayLabel,
    items: value.items,
  }));
}

function defaultTomorrowLocalInput(offsetMinutes: number): string {
  const target = new Date(Date.now() + 24 * 60 * 60 * 1000);
  target.setHours(10, 0, 0, 0);
  target.setMinutes(target.getMinutes() + offsetMinutes);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}T${pad(target.getHours())}:${pad(target.getMinutes())}`;
}

export function WeeklyCalendarCard({
  compact = false,
  redirectTo = "/calendar",
}: WeeklyCalendarCardProps) {
  const calendarStatusQuery = useCalendarStatus();
  const isConnected = Boolean(calendarStatusQuery.data?.connected);
  const calendarEventsQuery = useCalendarEvents(isConnected, 7, 50);
  const approvalsQuery = useApprovalsList("PENDING");

  const connectMutation = useConnectCalendarMutation();
  const disconnectMutation = useDisconnectCalendarMutation();
  const createEventMutation = useCreateCalendarEventMutation();
  const approveMutation = useApproveActionMutation();
  const rejectMutation = useRejectActionMutation();

  const [showAddForm, setShowAddForm] = useState(false);
  const [summary, setSummary] = useState("");
  const [startLocal, setStartLocal] = useState(() => defaultTomorrowLocalInput(0));
  const [endLocal, setEndLocal] = useState(() => defaultTomorrowLocalInput(45));
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const now = new Date();
  const weekEnd = new Date(now.getTime() + SEVEN_DAYS_MS);
  const windowLabel = `${now.toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${weekEnd.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;

  const groupedDays = groupEventsByDay(calendarEventsQuery.data?.items ?? [], now);
  const totalScheduledThisWeek = groupedDays.reduce((acc, g) => acc + g.items.length, 0);

  const pendingCalendarApprovals = (approvalsQuery.data?.items ?? []).filter(
    (item) => item.action_type === "create_calendar_event" && item.status === "PENDING"
  );

  const handleConnect = async () => {
    setActionError(null);
    try {
      const res = await connectMutation.mutateAsync(redirectTo);
      window.location.assign(res.authorization_url);
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Unable to start Google Calendar authorization."
      );
    }
  };

  const handleCreateEvent = async (e: FormEvent) => {
    e.preventDefault();
    setActionError(null);
    const trimmedSummary = summary.trim();
    if (trimmedSummary.length < 2) {
      setActionError("Enter an event title of at least 2 characters.");
      return;
    }
    const startDate = new Date(startLocal);
    const endDate = new Date(endLocal);
    if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
      setActionError("Enter valid start and end times.");
      return;
    }
    if (endDate <= startDate) {
      setActionError("End time must be after start time.");
      return;
    }
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      await createEventMutation.mutateAsync({
        summary: trimmedSummary,
        start_iso: startDate.toISOString(),
        end_iso: endDate.toISOString(),
        location: location.trim() || null,
        description: description.trim() || null,
        timezone: tz,
      });
      setSummary("");
      setLocation("");
      setDescription("");
      setShowAddForm(false);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to create Google Calendar event.");
    }
  };

  return (
    <Card
      title="This Week's Calendar (Next 7 Days)"
      subtitle={`Scheduled events from now through 1 week ahead (${windowLabel})`}
      action={
        isConnected ? (
          <StatusBadge label="CONNECTED" tone="success" />
        ) : (
          <StatusBadge label="DISCONNECTED" tone="neutral" />
        )
      }
    >
      <div className="space-y-4">
        {actionError && (
          <StateNotice title="Calendar notice" description={actionError} tone="error" />
        )}

        {calendarStatusQuery.error && (
          <StateNotice
            title="Could not load calendar status"
            description={calendarStatusQuery.error.message}
            tone="error"
          />
        )}

        {isConnected ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
              <span className="truncate">
                Account: <strong>{calendarStatusQuery.data?.google_email ?? "Google"}</strong> ·{" "}
                <strong>{totalScheduledThisWeek}</strong> event(s) this week
              </span>
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => void calendarEventsQuery.refetch()}
                  disabled={calendarEventsQuery.isFetching}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  <RefreshCw
                    className={`h-3 w-3 ${calendarEventsQuery.isFetching ? "animate-spin" : ""}`}
                    aria-hidden="true"
                  />
                  Refresh
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddForm((prev) => !prev)}
                  className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 hover:bg-indigo-100"
                >
                  <CalendarPlus className="h-3 w-3" aria-hidden="true" />
                  {showAddForm ? "Close" : "Add Event"}
                </button>
                <button
                  type="button"
                  onClick={() => void disconnectMutation.mutateAsync()}
                  disabled={disconnectMutation.isPending}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-600 hover:bg-slate-50"
                >
                  <Unlink className="h-3 w-3" aria-hidden="true" />
                  Disconnect
                </button>
              </div>
            </div>

            {showAddForm && (
              <form
                onSubmit={(e) => void handleCreateEvent(e)}
                className="space-y-3 rounded-xl border border-indigo-200 bg-indigo-50/40 p-3 text-xs"
              >
                <p className="font-semibold text-slate-900">Add Google Calendar Event</p>
                <div className="grid gap-2.5 sm:grid-cols-2">
                  <div className="sm:col-span-2">
                    <label htmlFor="cal-add-summary" className="block font-medium text-slate-700">
                      Event Title
                    </label>
                    <input
                      id="cal-add-summary"
                      type="text"
                      required
                      value={summary}
                      onChange={(e) => setSummary(e.target.value)}
                      placeholder="e.g., Technical Interview Prep"
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label htmlFor="cal-add-start" className="block font-medium text-slate-700">
                      Start Time
                    </label>
                    <input
                      id="cal-add-start"
                      type="datetime-local"
                      required
                      value={startLocal}
                      onChange={(e) => setStartLocal(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label htmlFor="cal-add-end" className="block font-medium text-slate-700">
                      End Time
                    </label>
                    <input
                      id="cal-add-end"
                      type="datetime-local"
                      required
                      value={endLocal}
                      onChange={(e) => setEndLocal(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label htmlFor="cal-add-location" className="block font-medium text-slate-700">
                      Location (optional)
                    </label>
                    <input
                      id="cal-add-location"
                      type="text"
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      placeholder="Google Meet / Office"
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label htmlFor="cal-add-desc" className="block font-medium text-slate-700">
                      Notes (optional)
                    </label>
                    <input
                      id="cal-add-desc"
                      type="text"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Topics or meeting link"
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="submit"
                    disabled={createEventMutation.isPending}
                    className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {createEventMutation.isPending ? "Saving..." : "Save to Google Calendar"}
                  </button>
                </div>
              </form>
            )}

            {calendarEventsQuery.error && (
              <StateNotice
                title="Unable to fetch Google Calendar events"
                description={calendarEventsQuery.error.message}
                tone="error"
              />
            )}

            {calendarEventsQuery.isPending ? (
              <p className="text-xs text-slate-500">
                Loading your scheduled events for the next 7 days...
              </p>
            ) : groupedDays.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/70 p-3 text-xs text-slate-600">
                No scheduled events on Google Calendar for the next 7 days ({windowLabel}).
              </div>
            ) : (
              <div className={compact ? "max-h-72 space-y-3 overflow-y-auto pr-1" : "space-y-4"}>
                {groupedDays.map((group) => (
                  <div key={group.dayKey} className="space-y-1.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-indigo-700">
                      <CalendarClock className="h-3.5 w-3.5" aria-hidden="true" />
                      <span>{group.dayLabel}</span>
                    </div>
                    <ul className="space-y-1.5">
                      {group.items.map((evt) => (
                        <li
                          key={`${evt.event_id}-${evt.start_iso}`}
                          className="rounded-lg border border-slate-200 bg-slate-50/80 p-2.5 text-xs transition-colors hover:border-indigo-200 hover:bg-white"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <p className="font-semibold text-slate-900">{evt.summary}</p>
                            <div className="flex shrink-0 items-center gap-1.5">
                              <StatusBadge
                                label={evt.status}
                                tone={evt.status === "cancelled" ? "danger" : "success"}
                              />
                              {evt.html_link && (
                                <a
                                  href={evt.html_link}
                                  target="_blank"
                                  rel="noreferrer"
                                  aria-label={`Open ${evt.summary} in Google Calendar`}
                                  className="inline-flex items-center gap-0.5 text-[11px] font-medium text-indigo-600 hover:text-indigo-800"
                                >
                                  <ExternalLink className="h-3 w-3" />
                                </a>
                              )}
                            </div>
                          </div>
                          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-600">
                            <span className="inline-flex items-center gap-1 font-medium text-slate-700">
                              <Clock className="h-3 w-3 text-indigo-500" aria-hidden="true" />
                              {formatTimeRange(evt.start_iso, evt.end_iso)}
                            </span>
                            {evt.location && (
                              <span className="inline-flex items-center gap-1 truncate">
                                <MapPin className="h-3 w-3 text-slate-400" aria-hidden="true" />
                                {evt.location}
                              </span>
                            )}
                          </div>
                          {!compact && evt.description && (
                            <p className="mt-1.5 line-clamp-2 text-[11px] text-slate-500">
                              {evt.description}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}

            {pendingCalendarApprovals.length > 0 && (
              <div className="space-y-2 border-t border-slate-200 pt-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-800">
                  Pending Calendar Confirmations ({pendingCalendarApprovals.length})
                </p>
                {pendingCalendarApprovals.map((apr) => {
                  const rawStart =
                    typeof apr.payload?.start_iso === "string" ? apr.payload.start_iso : null;
                  const rawEnd =
                    typeof apr.payload?.end_iso === "string" ? apr.payload.end_iso : null;
                  return (
                    <div
                      key={apr.id}
                      className="rounded-lg border border-amber-200 bg-amber-50/70 p-2.5 text-xs"
                    >
                      <p className="font-semibold text-slate-900">{apr.title}</p>
                      {rawStart && rawEnd && (
                        <p className="mt-0.5 text-[11px] text-slate-600">
                          {formatDayGroupHeader(rawStart, now)} · {formatTimeRange(rawStart, rawEnd)}
                        </p>
                      )}
                      <div className="mt-2 flex items-center gap-2">
                        <button
                          type="button"
                          disabled={approveMutation.isPending || rejectMutation.isPending}
                          onClick={() =>
                            void approveMutation.mutateAsync({
                              approvalId: apr.id,
                              note: "Approved from Weekly Calendar",
                            })
                          }
                          className="rounded-md bg-emerald-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                        >
                          Approve &amp; Add
                        </button>
                        <button
                          type="button"
                          disabled={approveMutation.isPending || rejectMutation.isPending}
                          onClick={() =>
                            void rejectMutation.mutateAsync({
                              approvalId: apr.id,
                              note: "Rejected from Weekly Calendar",
                            })
                          }
                          className="rounded-md border border-rose-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-slate-600">
              Connect Google Calendar to view all scheduled events within 1 week from now and let
              JobMate AI Co-Pilot propose interview &amp; prep blocks with your confirmation.
            </p>
            <button
              type="button"
              onClick={() => void handleConnect()}
              disabled={connectMutation.isPending}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
            >
              <Calendar className="h-4 w-4" aria-hidden="true" />
              {connectMutation.isPending
                ? "Redirecting to Google..."
                : "Connect Google Calendar"}
            </button>
          </div>
        )}
      </div>
    </Card>
  );
}
