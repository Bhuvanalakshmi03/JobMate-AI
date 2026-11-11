import { ArrowLeft, CheckCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import type { FactPatchItem } from "../../../types/resume";
import { ResumeFactCard } from "../components/ResumeFactCard";
import {
  useAnalyzeResumeMutation,
  usePatchFactsMutation,
  useResumeAnalysis,
} from "../hooks/useResumes";

export function ResumeAnalysisPage() {
  const { resumeId = "" } = useParams<{ resumeId: string }>();
  const analysisQuery = useResumeAnalysis(resumeId);
  const analyzeMutation = useAnalyzeResumeMutation();
  const patchMutation = usePatchFactsMutation(resumeId);
  const [syncToProfile, setSyncToProfile] = useState(true);

  const data = analysisQuery.data;
  const summary = data?.analysis_summary;
  const facts = data?.facts ?? [];
  const pendingFacts = facts.filter((f) => f.verification_status === "pending");

  const handleFactAction = async (patch: FactPatchItem) => {
    await patchMutation.mutateAsync({ updates: [patch], syncToProfile });
  };

  const handleVerifyAllPending = async () => {
    if (pendingFacts.length === 0) return;
    await patchMutation.mutateAsync({
      updates: pendingFacts.map((f) => ({ fact_id: f.id, action: "verify" })),
      syncToProfile,
    });
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link
            to="/resumes"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
            Back to Resumes
          </Link>
          <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-slate-900">
            {data?.resume.original_filename ?? "Resume Analysis & Fact Verification"}
          </h1>
        </div>

        <button
          type="button"
          disabled={analyzeMutation.isPending || !resumeId}
          onClick={() => void analyzeMutation.mutateAsync({ resumeId, force: true })}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <Sparkles className="h-4 w-4 text-indigo-600" aria-hidden="true" />
          {analyzeMutation.isPending ? "Re-analyzing..." : "Re-run Analysis"}
        </button>
      </div>

      {analysisQuery.isPending && (
        <StateNotice
          title="Loading resume analysis..."
          description="Fetching extracted facts and completeness assessment."
          tone="info"
        />
      )}

      {analysisQuery.error && (
        <StateNotice
          title="Unable to load resume analysis"
          description={analysisQuery.error.message}
          tone="error"
        />
      )}

      {analyzeMutation.error && (
        <StateNotice
          title="Analysis failed"
          description={analyzeMutation.error.message}
          tone="error"
        />
      )}

      {patchMutation.error && (
        <StateNotice
          title="Verification update failed"
          description={patchMutation.error.message}
          tone="error"
        />
      )}

      {patchMutation.isSuccess && !patchMutation.error && (
        <StateNotice
          title="Verification saved"
          description={`Verified facts: ${patchMutation.data.verified_count}. ${
            patchMutation.data.synced_to_profile
              ? `Synced ${patchMutation.data.synced_skills_count} skill(s) and verified details to your Career Profile.`
              : ""
          }`}
          tone="info"
        />
      )}

      {data && !summary && (
        <StateNotice
          title="Resume has not been analyzed yet"
          description="Click Re-run Analysis above to extract skills, education, projects, and recommendations."
          tone="empty"
        />
      )}

      {data && summary && (
        <div className="grid gap-5 md:grid-cols-2">
          <Card
            title="Completeness & Overview"
            action={
              data.completeness_score != null ? (
                <StatusBadge label={`${Math.round(data.completeness_score)} / 100`} tone="info" />
              ) : null
            }
          >
            <p className="text-sm leading-relaxed text-slate-700">
              {summary.overall_assessment ?? "Analysis completed."}
            </p>
            {summary.missing_skills && summary.missing_skills.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Suggested Missing Skills
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {summary.missing_skills.map((skill) => (
                    <StatusBadge key={skill} label={skill} tone="warning" />
                  ))}
                </div>
              </div>
            )}
          </Card>

          <Card title="Strengths & Recommendations">
            <div className="space-y-3 text-sm">
              {summary.strengths && summary.strengths.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                    Strengths
                  </p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-slate-700">
                    {summary.strengths.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
              {summary.recommendations && summary.recommendations.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
                    Improvements
                  </p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-slate-700">
                    {summary.recommendations.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {data && (
        <Card
          title={`Extracted Career Facts (${facts.length})`}
          subtitle="Only verified or edited facts are synced to your trusted Career Profile."
          action={
            <div className="flex flex-wrap items-center gap-3">
              <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={syncToProfile}
                  onChange={(e) => setSyncToProfile(e.target.checked)}
                />
                Sync verified facts to profile
              </label>
              {pendingFacts.length > 0 && (
                <button
                  type="button"
                  disabled={patchMutation.isPending}
                  onClick={() => void handleVerifyAllPending()}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  <CheckCheck className="h-3.5 w-3.5" aria-hidden="true" />
                  Verify All Pending ({pendingFacts.length})
                </button>
              )}
            </div>
          }
        >
          {facts.length === 0 ? (
            <StateNotice
              title="No extracted facts available"
              description="Run AI analysis to extract structured education, project, experience, and skill facts."
              tone="empty"
            />
          ) : (
            <div className="space-y-3">
              {facts.map((fact) => (
                <ResumeFactCard
                  key={fact.id}
                  fact={fact}
                  isSubmitting={patchMutation.isPending}
                  onAction={handleFactAction}
                />
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
