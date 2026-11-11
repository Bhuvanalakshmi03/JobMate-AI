import { ArrowLeft, Award, CheckCircle2, PlusCircle, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { interviewStatusTone } from "../../../types/interview";
import { formatDisplayDate } from "../../applications/utils/dates";
import {
  useEvaluateInterviewMutation,
  useGenerateQuestionsMutation,
  useInterviewDetail,
  useSubmitAnswerMutation,
} from "../hooks/useInterviews";

export function InterviewSessionPage() {
  const { sessionId = "" } = useParams();
  const detailQuery = useInterviewDetail(sessionId);
  const generateMutation = useGenerateQuestionsMutation(sessionId);
  const submitAnswerMutation = useSubmitAnswerMutation(sessionId);
  const evaluateMutation = useEvaluateInterviewMutation(sessionId);

  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [savedNotice, setSavedNotice] = useState<string | null>(null);

  const detail = detailQuery.data;

  useEffect(() => {
    if (!detail) return;
    setDrafts((prev) => {
      const next = { ...prev };
      for (const ans of detail.answers) {
        if (next[ans.question_id] === undefined) {
          next[ans.question_id] = ans.answer_text;
        }
      }
      return next;
    });
  }, [detail]);

  const handleSaveAnswer = async (questionId: string) => {
    const text = (drafts[questionId] ?? "").trim();
    if (text.length < 5) return;
    setSavedNotice(null);
    try {
      await submitAnswerMutation.mutateAsync({
        question_id: questionId,
        answer_text: text,
      });
      setSavedNotice("Answer saved cleanly.");
    } catch {
      // Displayed via submitAnswerMutation.error
    }
  };

  if (detailQuery.isPending) {
    return (
      <StateNotice
        title="Loading interview session..."
        description="Fetching questions, submitted answers, and rubric feedback."
        tone="info"
      />
    );
  }

  if (detailQuery.error || !detail) {
    return (
      <StateNotice
        title="Unable to load interview session"
        description={detailQuery.error?.message ?? "Session not found."}
        tone="error"
      />
    );
  }

  const { session, questions, answers, feedback } = detail;
  const answerByQuestionId = new Map(answers.map((a) => [a.question_id, a]));
  const evalByQuestionId = new Map(
    (feedback?.question_evaluations ?? []).map((item) => [item.question_id, item])
  );

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            to="/interviews"
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
            Back to Mock Interviews
          </Link>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">{session.title}</h1>
          <p className="text-sm text-slate-600">
            {session.target_role}
            {session.company_name ? ` · ${session.company_name}` : ""} · {session.focus_area} ·{" "}
            {session.difficulty}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label={session.status} tone={interviewStatusTone(session.status)} />
          <button
            type="button"
            disabled={generateMutation.isPending}
            onClick={() => void generateMutation.mutateAsync({ count: 3 })}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <PlusCircle className="h-3.5 w-3.5" aria-hidden="true" />
            {generateMutation.isPending ? "Generating..." : "Add 3 Questions"}
          </button>
          <button
            type="button"
            disabled={evaluateMutation.isPending || answers.length === 0}
            onClick={() => void evaluateMutation.mutateAsync()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            <Award className="h-3.5 w-3.5" aria-hidden="true" />
            {evaluateMutation.isPending ? "Evaluating..." : "Evaluate with Rubric"}
          </button>
        </div>
      </div>

      {savedNotice && (
        <StateNotice
          title={savedNotice}
          description="Your response has been saved to this mock interview session."
          tone="info"
        />
      )}

      {(submitAnswerMutation.error || evaluateMutation.error || generateMutation.error) && (
        <StateNotice
          title="Interview action notice"
          description={
            submitAnswerMutation.error?.message ??
            evaluateMutation.error?.message ??
            generateMutation.error?.message ??
            "Operation failed."
          }
          tone="error"
        />
      )}

      {feedback && (
        <Card
          title={`Evaluation Report — ${feedback.overall_score}% Overall`}
          subtitle={`Evaluated ${formatDisplayDate(feedback.evaluated_at)}`}
          action={<StatusBadge label={`${feedback.overall_score}%`} tone="success" />}
        >
          <div className="space-y-4">
            <p className="text-sm text-slate-700">{feedback.summary}</p>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {Object.entries(feedback.rubric_scores).map(([criterion, score]) => (
                <div key={criterion} className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs capitalize text-slate-500">
                    {criterion.replaceAll("_", " ")}
                  </p>
                  <p className="mt-1 text-lg font-bold text-indigo-700">{score}%</p>
                </div>
              ))}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-3 text-xs">
                <p className="font-semibold text-emerald-900">Key Strengths</p>
                <ul className="mt-1.5 list-disc space-y-1 pl-4 text-emerald-800">
                  {feedback.strengths.map((s, idx) => (
                    <li key={idx}>{s}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-3 text-xs">
                <p className="font-semibold text-amber-900">Areas to Strengthen</p>
                <ul className="mt-1.5 list-disc space-y-1 pl-4 text-amber-800">
                  {feedback.weaknesses.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </Card>
      )}

      <div className="space-y-4">
        {questions.map((q) => {
          const existingAns = answerByQuestionId.get(q.id);
          const qEval = evalByQuestionId.get(q.id);
          const currentDraft = drafts[q.id] ?? existingAns?.answer_text ?? "";

          return (
            <Card
              key={q.id}
              title={`Question ${q.order_index} · ${q.category.toUpperCase()}`}
              subtitle={q.guidance ?? undefined}
              action={
                existingAns ? (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                    <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                    Answered
                  </span>
                ) : (
                  <StatusBadge label="PENDING" tone="neutral" />
                )
              }
            >
              <div className="space-y-3">
                <p className="text-sm font-medium text-slate-900">{q.prompt}</p>

                {q.expected_topics.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {q.expected_topics.map((topic) => (
                      <span
                        key={topic}
                        className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-[11px] font-medium text-indigo-700"
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                )}

                <div>
                  <label htmlFor={`ans-${q.id}`} className="sr-only">
                    Answer for question {q.order_index}
                  </label>
                  <textarea
                    id={`ans-${q.id}`}
                    rows={4}
                    value={currentDraft}
                    onChange={(e) =>
                      setDrafts((prev) => ({
                        ...prev,
                        [q.id]: e.target.value,
                      }))
                    }
                    placeholder="Write your structured answer here (use STAR method for behavioral questions)..."
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                <div className="flex justify-end">
                  <button
                    type="button"
                    disabled={submitAnswerMutation.isPending || currentDraft.trim().length < 5}
                    onClick={() => void handleSaveAnswer(q.id)}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    <Send className="h-3.5 w-3.5" aria-hidden="true" />
                    Save Answer
                  </button>
                </div>

                {qEval && (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
                    <div className="flex items-center justify-between font-semibold text-slate-900">
                      <span>Question Score</span>
                      <span className="text-indigo-700">{qEval.score}%</span>
                    </div>
                    {qEval.improvements.length > 0 && (
                      <p className="mt-1 text-slate-600">
                        Improvements: {qEval.improvements.join(" · ")}
                      </p>
                    )}
                    {qEval.sample_strong_points.length > 0 && (
                      <p className="mt-1 text-emerald-700">
                        Strong points to hit: {qEval.sample_strong_points.join(" · ")}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
