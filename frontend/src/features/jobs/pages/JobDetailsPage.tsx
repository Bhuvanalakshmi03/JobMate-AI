import { ArrowLeft, Bookmark, ClipboardPlus, ExternalLink, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import type { JobMatch } from "../../../types/job";
import { useCreateApplicationMutation } from "../../applications/hooks/useApplications";
import { MatchScore } from "../components/MatchScore";
import {
  useCalculateJobMatchMutation,
  useJobDetail,
  useToggleSaveJobMutation,
} from "../hooks/useJobs";

export function JobDetailsPage() {
  const { jobId = "" } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const detailQuery = useJobDetail(jobId);
  const matchMutation = useCalculateJobMatchMutation();
  const saveMutation = useToggleSaveJobMutation();
  const trackMutation = useCreateApplicationMutation();
  const [computedMatch, setComputedMatch] = useState<JobMatch | null>(null);

  const job = detailQuery.data;

  const handleMatch = async () => {
    if (!jobId) return;
    const result = await matchMutation.mutateAsync(jobId);
    setComputedMatch(result);
  };

  const handleTrackApplication = async () => {
    if (!job) return;
    try {
      const created = await trackMutation.mutateAsync({
        job_id: job.id,
        company_name: job.company,
        role_title: job.title,
        location: job.location,
        job_url: job.external_url,
      });
      navigate(`/applications/${created.id}`);
    } catch {
      // Displayed via trackMutation.error
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Link
        to="/jobs"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-700"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        Back to Job Discovery
      </Link>

      {detailQuery.isPending && (
        <StateNotice
          title="Loading job details..."
          description="Fetching normalized job description and requirements."
          tone="info"
        />
      )}

      {detailQuery.error && (
        <StateNotice
          title="Unable to load job details"
          description={detailQuery.error.message}
          tone="error"
        />
      )}

      {job && (
        <>
          <Card
            title={job.title}
            subtitle={`${job.company}${job.location ? ` · ${job.location}` : ""}`}
            action={
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  disabled={matchMutation.isPending}
                  onClick={() => void handleMatch()}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                  {matchMutation.isPending ? "Calculating..." : "Calculate Match"}
                </button>
                <button
                  type="button"
                  disabled={saveMutation.isPending}
                  onClick={() =>
                    void saveMutation.mutateAsync({ jobId: job.id, isSaved: job.is_saved })
                  }
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  <Bookmark className="h-3.5 w-3.5" aria-hidden="true" />
                  {job.is_saved ? "Saved" : "Save"}
                </button>
                <a
                  href={job.external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Apply Externally
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                </a>
                <Link
                  to={`/documents?jobId=${job.id}`}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
                >
                  Tailor Documents
                </Link>
                <button
                  type="button"
                  disabled={trackMutation.isPending}
                  onClick={() => void handleTrackApplication()}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
                >
                  <ClipboardPlus className="h-3.5 w-3.5" aria-hidden="true" />
                  {trackMutation.isPending ? "Tracking..." : "Track Application"}
                </button>
              </div>
            }
          >
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <StatusBadge label={job.work_mode} tone="neutral" />
                <StatusBadge label={job.experience_level.replace("_", " ")} tone="neutral" />
                <StatusBadge label={job.employment_type.replace("_", " ")} tone="neutral" />
                {job.source_domain && <StatusBadge label={`Source: ${job.source_domain}`} tone="info" />}
                {job.salary_range && <StatusBadge label={job.salary_range} tone="success" />}
              </div>

              {job.requirements_summary && (
                <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
                  <span className="font-semibold text-slate-900">Requirements summary: </span>
                  {job.requirements_summary}
                </div>
              )}

              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Job Description
                </h3>
                <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-700">
                  {job.description}
                </p>
              </div>
            </div>
          </Card>

          {trackMutation.error && (
            <StateNotice
              title="Unable to track application"
              description={trackMutation.error.message}
              tone="error"
            />
          )}

          {matchMutation.error && (
            <StateNotice
              title="Match calculation failed"
              description={matchMutation.error.message}
              tone="error"
            />
          )}

          {computedMatch && <MatchScore match={computedMatch} />}
        </>
      )}
    </div>
  );
}
