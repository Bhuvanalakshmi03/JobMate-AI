import { Bookmark, ExternalLink, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../../../components/ui/StatusBadge";
import type { JobSummary } from "../../../types/job";
import { scoreTone } from "./MatchScore";

interface JobCardProps {
  job: JobSummary;
  isMatching: boolean;
  isSaving: boolean;
  onCalculateMatch: (jobId: string) => void;
  onToggleSave: (jobId: string, isSaved: boolean) => void;
}

export function JobCard({
  job,
  isMatching,
  isSaving,
  onCalculateMatch,
  onToggleSave,
}: JobCardProps) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to={`/jobs/${job.id}`}
              className="text-base font-semibold text-slate-900 hover:text-indigo-600"
            >
              {job.title}
            </Link>
            {job.match_preview && (
              <StatusBadge
                label={`${Math.round(job.match_preview.overall_score)}% Match`}
                tone={scoreTone(job.match_preview.overall_score)}
              />
            )}
          </div>
          <p className="mt-1 text-sm text-slate-600">
            {job.company}
            {job.location ? ` · ${job.location}` : ""}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <StatusBadge label={job.work_mode} tone="neutral" />
            <StatusBadge label={job.experience_level.replace("_", " ")} tone="neutral" />
            {job.source_domain && <StatusBadge label={job.source_domain} tone="info" />}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={isMatching}
            onClick={() => onCalculateMatch(job.id)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            {isMatching ? "Matching..." : "Match Score"}
          </button>

          <button
            type="button"
            disabled={isSaving}
            onClick={() => onToggleSave(job.id, job.is_saved)}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${
              job.is_saved
                ? "border-indigo-200 bg-indigo-50 text-indigo-700"
                : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
            }`}
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
            Apply
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
          </a>
        </div>
      </div>

      {job.required_skills.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5 border-t border-slate-100 pt-3">
          {job.required_skills.slice(0, 8).map((skill) => (
            <span
              key={skill}
              className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700"
            >
              {skill}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
