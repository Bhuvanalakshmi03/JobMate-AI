import { ArrowLeft, Check, ExternalLink, FileText, Save, Trash2 } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  applicationStatusLabel,
  applicationStatusTone,
  type ApplicationStatus,
} from "../../../types/application";
import { useDocumentsList } from "../../documents/hooks/useDocuments";
import {
  useApplicationDetail,
  useDeleteApplicationMutation,
  useTransitionApplicationMutation,
  useUpdateApplicationMutation,
} from "../hooks/useApplications";
import {
  formatDisplayDate,
  fromDatetimeLocalValue,
  toDatetimeLocalValue,
} from "../utils/dates";

export function ApplicationDetailsPage() {
  const { applicationId = "" } = useParams<{ applicationId: string }>();
  const navigate = useNavigate();

  const detailQuery = useApplicationDetail(applicationId);
  const docsQuery = useDocumentsList();
  const updateMutation = useUpdateApplicationMutation(applicationId);
  const transitionMutation = useTransitionApplicationMutation();
  const deleteMutation = useDeleteApplicationMutation();

  const [companyName, setCompanyName] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [location, setLocation] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [deadlineInput, setDeadlineInput] = useState("");
  const [followUpInput, setFollowUpInput] = useState("");
  const [tailoredResumeId, setTailoredResumeId] = useState("");
  const [coverLetterId, setCoverLetterId] = useState("");
  const [notes, setNotes] = useState("");

  const [transitionNote, setTransitionNote] = useState("");
  const [savedNotice, setSavedNotice] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const app = detailQuery.data;

  useEffect(() => {
    if (!app) return;
    setCompanyName(app.company_name);
    setRoleTitle(app.role_title);
    setLocation(app.location ?? "");
    setJobUrl(app.job_url ?? "");
    setDeadlineInput(toDatetimeLocalValue(app.deadline_at));
    setFollowUpInput(toDatetimeLocalValue(app.follow_up_at));
    setTailoredResumeId(app.tailored_resume_id ?? "");
    setCoverLetterId(app.cover_letter_id ?? "");
    setNotes(app.notes ?? "");
  }, [app]);

  const handleSaveDetails = async (e: FormEvent) => {
    e.preventDefault();
    if (!companyName.trim() || !roleTitle.trim()) return;
    setSavedNotice(false);

    try {
      await updateMutation.mutateAsync({
        company_name: companyName.trim(),
        role_title: roleTitle.trim(),
        location: location.trim() || null,
        job_url: jobUrl.trim() || null,
        deadline_at: fromDatetimeLocalValue(deadlineInput),
        follow_up_at: fromDatetimeLocalValue(followUpInput),
        tailored_resume_id: tailoredResumeId || null,
        cover_letter_id: coverLetterId || null,
        notes: notes.trim() || null,
      });
      setSavedNotice(true);
    } catch {
      // Displayed via updateMutation.error
    }
  };

  const handleTransition = async (targetStatus: ApplicationStatus) => {
    if (!app) return;
    try {
      await transitionMutation.mutateAsync({
        applicationId: app.id,
        target_status: targetStatus,
        note: transitionNote.trim() || null,
      });
      setTransitionNote("");
    } catch {
      // Displayed via transitionMutation.error
    }
  };

  const handleDelete = async () => {
    if (!app) return;
    try {
      await deleteMutation.mutateAsync(app.id);
      navigate("/applications", { replace: true });
    } catch {
      // Displayed via deleteMutation.error
    }
  };

  const documents = docsQuery.data?.items ?? [];
  const resumeDocs = documents.filter((d) => d.document_type === "tailored_resume");
  const coverDocs = documents.filter(
    (d) => d.document_type === "cover_letter" || d.document_type === "application_note"
  );

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link
            to="/applications"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
            Back to Application Tracker
          </Link>
          <div className="mt-1.5 flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              {app ? `${app.role_title} — ${app.company_name}` : "Application Details"}
            </h1>
            {app && (
              <StatusBadge
                label={applicationStatusLabel(app.status)}
                tone={applicationStatusTone(app.status)}
              />
            )}
          </div>
        </div>

        {app && (
          <div className="flex flex-wrap items-center gap-2">
            {app.job_url && (
              <a
                href={app.job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                Open Job Listing
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
            )}
            {app.job_id && (
              <Link
                to={`/documents?jobId=${app.job_id}`}
                className="inline-flex items-center gap-1 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
              >
                <FileText className="h-3.5 w-3.5" aria-hidden="true" />
                Tailor Documents
              </Link>
            )}
          </div>
        )}
      </div>

      {detailQuery.isPending && (
        <StateNotice
          title="Loading application details..."
          description="Fetching application metadata and status transition history."
          tone="info"
        />
      )}

      {detailQuery.error && (
        <StateNotice
          title="Unable to load application"
          description={detailQuery.error.message}
          tone="error"
        />
      )}

      {app && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <Card
              title="Status & Controlled Workflow"
              subtitle="Only state-machine validated transitions are permitted from your current stage."
            >
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600">
                  <span>Current status: {applicationStatusLabel(app.status)}</span>
                  {app.applied_at && <span>Submitted: {formatDisplayDate(app.applied_at)}</span>}
                  <span>Created: {formatDisplayDate(app.created_at)}</span>
                </div>

                <div>
                  <label
                    htmlFor="transition-note"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Transition Note (optional)
                  </label>
                  <input
                    id="transition-note"
                    type="text"
                    value={transitionNote}
                    onChange={(e) => setTransitionNote(e.target.value)}
                    placeholder="e.g., Recruiter confirmed technical phone screen for Friday"
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                {app.allowed_next_statuses.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {app.allowed_next_statuses.map((nextStatus) => (
                      <button
                        key={nextStatus}
                        type="button"
                        disabled={transitionMutation.isPending}
                        onClick={() => void handleTransition(nextStatus)}
                        className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
                      >
                        Move to {applicationStatusLabel(nextStatus)}
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">
                    This application is in a terminal state. No further transitions are available.
                  </p>
                )}

                {transitionMutation.error && (
                  <StateNotice
                    title="Status transition failed"
                    description={transitionMutation.error.message}
                    tone="error"
                  />
                )}
              </div>
            </Card>

            <Card
              title="Application Details, Links & Reminders"
              subtitle="Update job metadata, deadlines, linked tailored documents, and notes."
            >
              <form onSubmit={(e) => void handleSaveDetails(e)} className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="detail-company"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Company Name
                    </label>
                    <input
                      id="detail-company"
                      type="text"
                      required
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="detail-role"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Role Title
                    </label>
                    <input
                      id="detail-role"
                      type="text"
                      required
                      value={roleTitle}
                      onChange={(e) => setRoleTitle(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="detail-location"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Location
                    </label>
                    <input
                      id="detail-location"
                      type="text"
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="detail-url"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Job URL
                    </label>
                    <input
                      id="detail-url"
                      type="url"
                      value={jobUrl}
                      onChange={(e) => setJobUrl(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="detail-deadline"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Deadline
                    </label>
                    <input
                      id="detail-deadline"
                      type="datetime-local"
                      value={deadlineInput}
                      onChange={(e) => setDeadlineInput(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="detail-followup"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Follow-up Reminder
                    </label>
                    <input
                      id="detail-followup"
                      type="datetime-local"
                      value={followUpInput}
                      onChange={(e) => setFollowUpInput(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="detail-resume-doc"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Linked Tailored Resume
                    </label>
                    <select
                      id="detail-resume-doc"
                      value={tailoredResumeId}
                      onChange={(e) => setTailoredResumeId(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                    >
                      <option value="">None linked</option>
                      {resumeDocs.map((doc) => (
                        <option key={doc.id} value={doc.id}>
                          {doc.title} (v{doc.version})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="detail-cover-doc"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Linked Cover Letter / Note
                    </label>
                    <select
                      id="detail-cover-doc"
                      value={coverLetterId}
                      onChange={(e) => setCoverLetterId(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                    >
                      <option value="">None linked</option>
                      {coverDocs.map((doc) => (
                        <option key={doc.id} value={doc.id}>
                          {doc.title} (v{doc.version})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label htmlFor="detail-notes" className="block text-xs font-medium text-slate-700">
                    Notes
                  </label>
                  <textarea
                    id="detail-notes"
                    rows={4}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                {updateMutation.error && (
                  <StateNotice
                    title="Update failed"
                    description={updateMutation.error.message}
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

                {savedNotice && (
                  <StateNotice
                    title="Changes saved"
                    description="Application metadata and reminders were updated."
                    tone="info"
                  />
                )}

                <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                  <div>
                    {confirmingDelete ? (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          disabled={deleteMutation.isPending}
                          onClick={() => void handleDelete()}
                          className="inline-flex items-center gap-1 rounded-lg bg-rose-600 px-3 py-2 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50"
                        >
                          <Check className="h-3.5 w-3.5" aria-hidden="true" />
                          Confirm Delete
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmingDelete(false)}
                          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setConfirmingDelete(true)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-3 py-2 text-xs font-medium text-rose-700 hover:bg-rose-50"
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                        Delete Application
                      </button>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={updateMutation.isPending}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    <Save className="h-4 w-4" aria-hidden="true" />
                    {updateMutation.isPending ? "Saving..." : "Save Changes"}
                  </button>
                </div>
              </form>
            </Card>
          </div>

          <div>
            <Card
              title="Activity History"
              subtitle={`${app.history.length} recorded state change(s)`}
            >
              {app.history.length === 0 ? (
                <p className="text-xs text-slate-500">No status history recorded yet.</p>
              ) : (
                <ol className="space-y-4 border-l border-slate-200 pl-4">
                  {app.history.map((entry) => (
                    <li key={entry.id} className="relative space-y-1">
                      <span
                        className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-indigo-500 ring-4 ring-white"
                        aria-hidden="true"
                      />
                      <p className="text-xs font-semibold text-slate-900">
                        {entry.from_status
                          ? `${applicationStatusLabel(entry.from_status)} → ${applicationStatusLabel(entry.to_status)}`
                          : `Created (${applicationStatusLabel(entry.to_status)})`}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {formatDisplayDate(entry.changed_at)}
                      </p>
                      {entry.note && (
                        <p className="rounded-md bg-slate-50 p-2 text-xs text-slate-700">
                          {entry.note}
                        </p>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
