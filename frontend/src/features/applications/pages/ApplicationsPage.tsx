import {
  CalendarClock,
  ExternalLink,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  APPLICATION_STATUS_ORDER,
  applicationStatusLabel,
  applicationStatusTone,
  type ApplicationStatus,
} from "../../../types/application";
import { useJobSearch } from "../../jobs/hooks/useJobs";
import {
  useApplicationsList,
  useApplicationSummary,
  useCreateApplicationMutation,
  useDeleteApplicationMutation,
  useTransitionApplicationMutation,
} from "../hooks/useApplications";
import { formatDisplayDate, fromDatetimeLocalValue } from "../utils/dates";

export function ApplicationsPage() {
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "">("");
  const [isFormOpen, setIsFormOpen] = useState(false);

  const [selectedJobId, setSelectedJobId] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [location, setLocation] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [deadlineInput, setDeadlineInput] = useState("");
  const [followUpInput, setFollowUpInput] = useState("");
  const [notes, setNotes] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const listQuery = useApplicationsList({
    status: statusFilter,
    limit: 50,
    offset: 0,
  });
  const summaryQuery = useApplicationSummary();
  const jobsQuery = useJobSearch({ limit: 30 }, isFormOpen);

  const createMutation = useCreateApplicationMutation();
  const transitionMutation = useTransitionApplicationMutation();
  const deleteMutation = useDeleteApplicationMutation();

  const resetForm = () => {
    setSelectedJobId("");
    setCompanyName("");
    setRoleTitle("");
    setLocation("");
    setJobUrl("");
    setDeadlineInput("");
    setFollowUpInput("");
    setNotes("");
    setValidationError(null);
  };

  const handleSelectDiscoveredJob = (jobId: string) => {
    setSelectedJobId(jobId);
    const match = jobsQuery.data?.items.find((item) => item.id === jobId);
    if (match) {
      setCompanyName(match.company);
      setRoleTitle(match.title);
      setLocation(match.location ?? "");
      setJobUrl(match.external_url);
    } else if (!jobId) {
      setCompanyName("");
      setRoleTitle("");
      setLocation("");
      setJobUrl("");
    }
  };

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    const trimmedCompany = companyName.trim();
    const trimmedRole = roleTitle.trim();
    const trimmedUrl = jobUrl.trim();

    if (!selectedJobId && (!trimmedCompany || !trimmedRole)) {
      setValidationError(
        "Enter both Company Name and Role Title, or select a discovered job listing."
      );
      return;
    }

    if (trimmedUrl && !trimmedUrl.startsWith("http://") && !trimmedUrl.startsWith("https://")) {
      setValidationError("Job URL must start with http:// or https://");
      return;
    }

    setValidationError(null);

    try {
      await createMutation.mutateAsync({
        job_id: selectedJobId || null,
        company_name: trimmedCompany || null,
        role_title: trimmedRole || null,
        location: location.trim() || null,
        job_url: trimmedUrl || null,
        deadline_at: fromDatetimeLocalValue(deadlineInput),
        follow_up_at: fromDatetimeLocalValue(followUpInput),
        notes: notes.trim() || null,
      });

      resetForm();
      setIsFormOpen(false);
    } catch {
      // Displayed via createMutation.error
    }
  };

  const handleQuickTransition = async (applicationId: string, nextStatus: ApplicationStatus) => {
    try {
      await transitionMutation.mutateAsync({
        applicationId,
        target_status: nextStatus,
      });
    } catch {
      // Displayed via transitionMutation.error
    }
  };

  const handleDelete = async (applicationId: string) => {
    try {
      await deleteMutation.mutateAsync(applicationId);
    } catch {
      // Displayed via deleteMutation.error
    }
  };

  const summary = summaryQuery.data;
  const applications = listQuery.data?.items ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Application Tracker</h1>
          <p className="mt-1 text-sm text-slate-600">
            Track job applications, deadlines, follow-ups, and controlled status transitions.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsFormOpen((open) => !open)}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
        >
          {isFormOpen ? (
            <>
              <X className="h-4 w-4" aria-hidden="true" />
              Close Form
            </>
          ) : (
            <>
              <Plus className="h-4 w-4" aria-hidden="true" />
              New Application
            </>
          )}
        </button>
      </header>

      {summary && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Total Tracked
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{summary.total_applications}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Submitted
            </p>
            <p className="mt-1 text-2xl font-bold text-emerald-700">
              {summary.counts_by_status["SUBMITTED"] ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Interviews
            </p>
            <p className="mt-1 text-2xl font-bold text-indigo-700">
              {summary.counts_by_status["INTERVIEW_SCHEDULED"] ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Upcoming Deadlines
            </p>
            <p className="mt-1 text-2xl font-bold text-amber-700">
              {summary.upcoming_deadlines.length}
            </p>
          </div>
        </div>
      )}

      {summary && summary.upcoming_deadlines.length > 0 && (
        <Card
          title="Upcoming Deadlines"
          subtitle="Active applications with upcoming submission or follow-up deadlines"
        >
          <ul className="divide-y divide-slate-100 text-sm">
            {summary.upcoming_deadlines.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-2 py-2.5 first:pt-0 last:pb-0"
              >
                <div>
                  <Link
                    to={`/applications/${item.id}`}
                    className="font-semibold text-slate-900 hover:text-indigo-600"
                  >
                    {item.role_title}
                  </Link>
                  <span className="ml-2 text-slate-600">at {item.company_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge
                    label={applicationStatusLabel(item.status)}
                    tone={applicationStatusTone(item.status)}
                  />
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700">
                    <CalendarClock className="h-3.5 w-3.5" aria-hidden="true" />
                    {formatDisplayDate(item.deadline_at)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {isFormOpen && (
        <Card
          title="Track New Application"
          subtitle="Link an existing discovered job listing or record a custom application."
        >
          <form onSubmit={(e) => void handleCreate(e)} className="space-y-4">
            <div>
              <label
                htmlFor="app-job-select"
                className="block text-xs font-medium text-slate-700"
              >
                Discovered Job Listing (optional)
              </label>
              <select
                id="app-job-select"
                value={selectedJobId}
                onChange={(e) => handleSelectDiscoveredJob(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              >
                <option value="">Custom entry (enter company and role manually)</option>
                {(jobsQuery.data?.items ?? []).map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.title} — {job.company}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="app-company"
                  className="block text-xs font-medium text-slate-700"
                >
                  Company Name
                </label>
                <input
                  id="app-company"
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g., Stripe"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="app-role"
                  className="block text-xs font-medium text-slate-700"
                >
                  Role Title
                </label>
                <input
                  id="app-role"
                  type="text"
                  value={roleTitle}
                  onChange={(e) => setRoleTitle(e.target.value)}
                  placeholder="e.g., Backend Software Engineer"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="app-location"
                  className="block text-xs font-medium text-slate-700"
                >
                  Location (optional)
                </label>
                <input
                  id="app-location"
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g., Bengaluru / Remote"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="app-url"
                  className="block text-xs font-medium text-slate-700"
                >
                  Job URL (optional)
                </label>
                <input
                  id="app-url"
                  type="url"
                  value={jobUrl}
                  onChange={(e) => setJobUrl(e.target.value)}
                  placeholder="https://example.com/jobs/123"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="app-deadline"
                  className="block text-xs font-medium text-slate-700"
                >
                  Application Deadline (optional)
                </label>
                <input
                  id="app-deadline"
                  type="datetime-local"
                  value={deadlineInput}
                  onChange={(e) => setDeadlineInput(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="app-followup"
                  className="block text-xs font-medium text-slate-700"
                >
                  Follow-up Reminder (optional)
                </label>
                <input
                  id="app-followup"
                  type="datetime-local"
                  value={followUpInput}
                  onChange={(e) => setFollowUpInput(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label htmlFor="app-notes" className="block text-xs font-medium text-slate-700">
                Personal Notes (optional)
              </label>
              <textarea
                id="app-notes"
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Recruiter contact, referral context, or tailored preparation notes..."
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              />
            </div>

            {validationError && (
              <StateNotice
                title="Missing or invalid details"
                description={validationError}
                tone="error"
              />
            )}

            {createMutation.error && (
              <StateNotice
                title="Could not create application"
                description={createMutation.error.message}
                tone="error"
              />
            )}

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  resetForm();
                  setIsFormOpen(false);
                }}
                className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {createMutation.isPending ? "Saving..." : "Save Application"}
              </button>
            </div>
          </form>
        </Card>
      )}

      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter applications by status">
        <button
          type="button"
          onClick={() => setStatusFilter("")}
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
            statusFilter === ""
              ? "bg-slate-900 text-white"
              : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
          }`}
        >
          All{summary ? ` (${summary.total_applications})` : ""}
        </button>
        {APPLICATION_STATUS_ORDER.map((status) => {
          const count = summary?.counts_by_status[status];
          return (
            <button
              key={status}
              type="button"
              onClick={() => setStatusFilter(status)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                statusFilter === status
                  ? "bg-indigo-600 text-white"
                  : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              {applicationStatusLabel(status)}
              {count !== undefined ? ` (${count})` : ""}
            </button>
          );
        })}
      </div>

      {transitionMutation.error && (
        <StateNotice
          title="Status update rejected"
          description={transitionMutation.error.message}
          tone="error"
        />
      )}

      {deleteMutation.error && (
        <StateNotice
          title="Delete failed"
          description={deleteMutation.error.message}
          tone="error"
        />
      )}

      <Card
        title="Tracked Applications"
        subtitle={
          listQuery.data
            ? `${listQuery.data.total} application(s)${statusFilter ? ` in ${applicationStatusLabel(statusFilter)}` : ""}`
            : undefined
        }
      >
        {listQuery.isPending && (
          <StateNotice
            title="Loading applications..."
            description="Fetching your application pipeline and deadlines."
            tone="info"
          />
        )}

        {listQuery.error && (
          <StateNotice
            title="Unable to load applications"
            description={listQuery.error.message}
            tone="error"
          />
        )}

        {!listQuery.isPending && !listQuery.error && applications.length === 0 && (
          <StateNotice
            title={
              statusFilter
                ? `No applications in "${applicationStatusLabel(statusFilter)}"`
                : "No tracked applications yet"
            }
            description='Track a job directly from Job Discovery or click "New Application" above to get started.'
            tone="info"
          />
        )}

        {!listQuery.isPending && !listQuery.error && applications.length > 0 && (
          <div className="space-y-4">
            {applications.map((item) => (
              <div
                key={item.id}
                className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 space-y-3"
              >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        to={`/applications/${item.id}`}
                        className="text-base font-semibold text-slate-900 hover:text-indigo-600"
                      >
                        {item.role_title}
                      </Link>
                      <StatusBadge
                        label={applicationStatusLabel(item.status)}
                        tone={applicationStatusTone(item.status)}
                      />
                    </div>
                    <p className="mt-0.5 text-sm text-slate-600">
                      {item.company_name}
                      {item.location ? ` · ${item.location}` : ""}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {item.job_url && (
                      <a
                        href={item.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                      >
                        Listing
                        <ExternalLink className="h-3 w-3" aria-hidden="true" />
                      </a>
                    )}
                    <Link
                      to={`/applications/${item.id}`}
                      className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
                    >
                      Details & History
                    </Link>
                    <button
                      type="button"
                      disabled={deleteMutation.isPending}
                      onClick={() => void handleDelete(item.id)}
                      aria-label={`Delete application for ${item.role_title}`}
                      className="inline-flex items-center gap-1 rounded-lg border border-rose-200 bg-white px-2.5 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                      Delete
                    </button>
                  </div>
                </div>

                <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500">
                  {item.deadline_at && (
                    <span>Deadline: {formatDisplayDate(item.deadline_at)}</span>
                  )}
                  {item.follow_up_at && (
                    <span>Follow-up: {formatDisplayDate(item.follow_up_at)}</span>
                  )}
                  {item.applied_at && <span>Submitted: {formatDisplayDate(item.applied_at)}</span>}
                  <span>Updated: {formatDisplayDate(item.updated_at)}</span>
                </div>

                {item.notes && (
                  <p className="line-clamp-2 text-xs text-slate-700">{item.notes}</p>
                )}

                {item.allowed_next_statuses.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-xs font-medium text-slate-500">Next stages:</span>
                    {item.allowed_next_statuses.map((nextStatus) => (
                      <button
                        key={nextStatus}
                        type="button"
                        disabled={transitionMutation.isPending}
                        onClick={() => void handleQuickTransition(item.id, nextStatus)}
                        className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 disabled:opacity-50"
                      >
                        Move to {applicationStatusLabel(nextStatus)}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
