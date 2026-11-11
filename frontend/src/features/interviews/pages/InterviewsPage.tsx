import { ArrowRight, GraduationCap, Play, Sparkles, Target, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  interviewStatusTone,
  type InterviewDifficulty,
  type InterviewFocusArea,
} from "../../../types/interview";
import { formatDisplayDate } from "../../applications/utils/dates";
import { useJobSearch } from "../../jobs/hooks/useJobs";
import {
  useCreateInterviewMutation,
  useDeleteInterviewMutation,
  useInterviewSessionsList,
  useSkillGapPlan,
} from "../hooks/useInterviews";

export function InterviewsPage() {
  const navigate = useNavigate();
  const sessionsQuery = useInterviewSessionsList();
  const gapQuery = useSkillGapPlan();
  const jobsQuery = useJobSearch({ limit: 30 }, true);

  const createMutation = useCreateInterviewMutation();
  const deleteMutation = useDeleteInterviewMutation();

  const [jobId, setJobId] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [focusArea, setFocusArea] = useState<InterviewFocusArea>("mixed");
  const [difficulty, setDifficulty] = useState<InterviewDifficulty>("entry");
  const [questionCount, setQuestionCount] = useState(5);
  const [validationError, setValidationError] = useState<string | null>(null);

  const sessions = sessionsQuery.data?.items ?? [];

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!jobId && targetRole.trim().length < 2) {
      setValidationError("Select a target job or enter a target role name.");
      return;
    }
    setValidationError(null);
    try {
      const created = await createMutation.mutateAsync({
        job_id: jobId || null,
        target_role: targetRole.trim() || null,
        company_name: companyName.trim() || null,
        focus_area: focusArea,
        difficulty,
        question_count: questionCount,
        generate_questions: true,
      });
      navigate(`/interviews/${created.session.id}`);
    } catch {
      // Displayed via createMutation.error
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Interview Preparation &amp; Skill Gaps
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Practice role-specific technical, behavioral, and HR mock interviews with rubric-based
          AI feedback and prioritized improvement plans.
        </p>
      </header>

      <Card
        title="Start New Mock Interview"
        subtitle="Generate targeted questions tailored to a discovered role and your verified background."
      >
        <form onSubmit={(e) => void handleCreate(e)} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label htmlFor="int-job" className="block text-xs font-medium text-slate-700">
                Target Job Listing (optional)
              </label>
              <select
                id="int-job"
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              >
                <option value="">Custom role below</option>
                {(jobsQuery.data?.items ?? []).map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.title} — {job.company}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="int-role" className="block text-xs font-medium text-slate-700">
                Target Role
              </label>
              <input
                id="int-role"
                type="text"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g., Junior AI & Backend Engineer"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="int-company" className="block text-xs font-medium text-slate-700">
                Company Name (optional)
              </label>
              <input
                id="int-company"
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g., Zoho Corporation"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="int-focus" className="block text-xs font-medium text-slate-700">
                Focus Area
              </label>
              <select
                id="int-focus"
                value={focusArea}
                onChange={(e) => setFocusArea(e.target.value as InterviewFocusArea)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              >
                <option value="mixed">Mixed (Technical + STAR Behavioral + HR)</option>
                <option value="technical">Technical Deep Dive</option>
                <option value="behavioral">Behavioral (STAR)</option>
                <option value="hr">HR &amp; Culture Fit</option>
              </select>
            </div>

            <div>
              <label htmlFor="int-diff" className="block text-xs font-medium text-slate-700">
                Difficulty
              </label>
              <select
                id="int-diff"
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as InterviewDifficulty)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              >
                <option value="entry">Entry / Internship</option>
                <option value="intermediate">Intermediate</option>
                <option value="senior">Senior / Architecture</option>
              </select>
            </div>

            <div>
              <label htmlFor="int-count" className="block text-xs font-medium text-slate-700">
                Questions Count
              </label>
              <select
                id="int-count"
                value={questionCount}
                onChange={(e) => setQuestionCount(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              >
                <option value={3}>3 Questions (Quick Drill)</option>
                <option value={5}>5 Questions (Standard)</option>
                <option value={8}>8 Questions (Full Panel)</option>
              </select>
            </div>
          </div>

          {validationError && (
            <StateNotice title="Invalid interview setup" description={validationError} tone="error" />
          )}

          {createMutation.error && (
            <StateNotice
              title="Unable to create mock interview"
              description={createMutation.error.message}
              tone="error"
            />
          )}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              <Play className="h-4 w-4" aria-hidden="true" />
              {createMutation.isPending ? "Generating Questions..." : "Start Mock Interview"}
            </button>
          </div>
        </form>
      </Card>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-6">
          <Card title="Mock Interview Sessions" subtitle={`${sessions.length} recorded session(s)`}>
            {sessionsQuery.isPending ? (
              <p className="text-xs text-slate-500">Loading sessions...</p>
            ) : sessionsQuery.error ? (
              <StateNotice
                title="Unable to load sessions"
                description={sessionsQuery.error.message}
                tone="error"
              />
            ) : sessions.length === 0 ? (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <GraduationCap className="h-4 w-4 text-indigo-500" aria-hidden="true" />
                <span>No mock interviews yet. Launch your first practice session above.</span>
              </div>
            ) : (
              <ul className="space-y-2.5">
                {sessions.map((item) => (
                  <li
                    key={item.id}
                    className="rounded-lg border border-slate-200 bg-white p-3.5 transition-colors hover:border-indigo-200"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <Link
                          to={`/interviews/${item.id}`}
                          className="text-sm font-semibold text-slate-900 hover:text-indigo-600"
                        >
                          {item.title}
                        </Link>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {item.focus_area} · {item.difficulty} · {item.question_count} question(s)
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {item.overall_score !== null && (
                          <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                            {item.overall_score}%
                          </span>
                        )}
                        <StatusBadge
                          label={item.status}
                          tone={interviewStatusTone(item.status)}
                        />
                      </div>
                    </div>
                    <div className="mt-2.5 flex items-center justify-between text-xs text-slate-400">
                      <span>{formatDisplayDate(item.updated_at)}</span>
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/interviews/${item.id}`}
                          className="inline-flex items-center gap-1 font-semibold text-indigo-600 hover:text-indigo-800"
                        >
                          Open <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                        </Link>
                        <button
                          type="button"
                          aria-label={`Delete session ${item.title}`}
                          onClick={() => void deleteMutation.mutateAsync(item.id)}
                          disabled={deleteMutation.isPending}
                          className="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="lg:col-span-6">
          <Card
            title="Skill Gap & Improvement Plan"
            subtitle="Prioritized from job match gaps and mock interview rubric evaluations"
          >
            {gapQuery.isPending ? (
              <p className="text-xs text-slate-500">Analyzing skill gaps...</p>
            ) : gapQuery.error ? (
              <StateNotice
                title="Unable to load skill gap plan"
                description={gapQuery.error.message}
                tone="error"
              />
            ) : gapQuery.data ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-slate-500">Evaluated Interviews</p>
                    <p className="mt-1 text-lg font-bold text-slate-900">
                      {gapQuery.data.evaluated_sessions_count}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-slate-500">Avg Interview Score</p>
                    <p className="mt-1 text-lg font-bold text-indigo-700">
                      {gapQuery.data.average_interview_score !== null
                        ? `${gapQuery.data.average_interview_score}%`
                        : "—"}
                    </p>
                  </div>
                </div>

                {gapQuery.data.missing_skills_from_matches.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Top Missing Skills from Job Matches
                    </p>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {gapQuery.data.missing_skills_from_matches.map((skill) => (
                        <span
                          key={skill}
                          className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {gapQuery.data.improvement_plan.length === 0 ? (
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Sparkles className="h-4 w-4 text-indigo-500" aria-hidden="true" />
                    <span>Complete a mock interview or calculate job matches to populate gaps.</span>
                  </div>
                ) : (
                  <ul className="space-y-2.5">
                    {gapQuery.data.improvement_plan.map((item) => (
                      <li
                        key={item.skill}
                        className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="inline-flex items-center gap-1.5 font-semibold text-slate-900">
                            <Target className="h-3.5 w-3.5 text-indigo-600" aria-hidden="true" />
                            {item.skill}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-[11px] text-slate-500">
                              ~{item.estimated_hours}h
                            </span>
                            <StatusBadge
                              label={item.priority.toUpperCase()}
                              tone={
                                item.priority === "high"
                                  ? "danger"
                                  : item.priority === "medium"
                                    ? "warning"
                                    : "neutral"
                              }
                            />
                          </div>
                        </div>
                        <p className="mt-1 text-slate-600">{item.current_gap}</p>
                        {item.action_items.length > 0 && (
                          <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-slate-700">
                            {item.action_items.map((act, idx) => (
                              <li key={idx}>{act}</li>
                            ))}
                          </ul>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  );
}
