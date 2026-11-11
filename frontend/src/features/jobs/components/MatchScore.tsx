import { Card } from "../../../components/ui/Card";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import type { JobMatch } from "../../../types/job";

const FACTOR_LABELS: Record<string, string> = {
  technical_skill_compatibility: "Technical Skills",
  job_role_similarity: "Role Alignment",
  relevant_experience_projects: "Verified Experience & Projects",
  experience_level_compatibility: "Experience Level",
  education_requirements: "Education Fit",
  location_preferences: "Location & Work Mode",
  job_freshness: "Posting Freshness",
  semantic_similarity: "Semantic Similarity",
};

export function scoreTone(score: number): "success" | "warning" | "danger" | "info" {
  if (score >= 75) return "success";
  if (score >= 50) return "info";
  if (score >= 30) return "warning";
  return "danger";
}

export function MatchScore({ match }: { match: JobMatch }) {
  return (
    <Card
      title="Explainable Job Match Breakdown"
      subtitle={`Scoring algorithm ${match.algorithm_version}`}
      action={
        <StatusBadge
          label={`${Math.round(match.overall_score)}% Match`}
          tone={scoreTone(match.overall_score)}
        />
      }
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-slate-700">{match.match_explanation}</p>

        <div className="space-y-2.5">
          {Object.entries(match.factor_scores).map(([key, value]) => {
            const pct = Math.round(value * 100);
            const weight = match.weights_used[key];
            return (
              <div key={key} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-700">
                    {FACTOR_LABELS[key] ?? key}
                    {typeof weight === "number" ? ` (${Math.round(weight * 100)}% weight)` : ""}
                  </span>
                  <span className="font-mono text-slate-600">{pct}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-indigo-600 transition-all"
                    style={{ width: `${Math.max(2, Math.min(100, pct))}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div className="grid gap-4 border-t border-slate-200 pt-4 sm:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
              Matching Skills ({match.matching_skills.length})
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {match.matching_skills.length > 0 ? (
                match.matching_skills.map((skill) => (
                  <StatusBadge key={skill} label={skill} tone="success" />
                ))
              ) : (
                <span className="text-xs text-slate-500">None matched yet</span>
              )}
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
              Missing Skills ({match.missing_skills.length})
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {match.missing_skills.length > 0 ? (
                match.missing_skills.map((skill) => (
                  <StatusBadge key={skill} label={skill} tone="warning" />
                ))
              ) : (
                <span className="text-xs text-slate-500">No missing required skills</span>
              )}
            </div>
          </div>
        </div>

        {match.recommended_preparation.length > 0 && (
          <div className="border-t border-slate-200 pt-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
              Recommended Preparation
            </p>
            <ul className="mt-1.5 list-disc space-y-1 pl-4 text-sm text-slate-700">
              {match.recommended_preparation.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  );
}
