import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InterviewSessionPage } from "../src/features/interviews/pages/InterviewSessionPage";
import { InterviewsPage } from "../src/features/interviews/pages/InterviewsPage";
import { interviewService } from "../src/services/interview-service";
import { jobService } from "../src/services/job-service";

function renderInterviewRoutes(initialEntry = "/interviews") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/interviews" element={<InterviewsPage />} />
          <Route path="/interviews/:sessionId" element={<InterviewSessionPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("InterviewsPage & InterviewSessionPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a mock interview session, renders skill gap plan, submits answers, and evaluates rubric", async () => {
    vi.spyOn(jobService, "searchJobs").mockResolvedValue({
      items: [],
      total: 0,
      source: "database",
      cached: false,
    });
    vi.spyOn(interviewService, "listSessions").mockResolvedValue({
      items: [],
      total: 0,
    });
    vi.spyOn(interviewService, "getSkillGapPlan").mockResolvedValue({
      verified_skills: ["Python"],
      missing_skills_from_matches: ["Redis", "Docker"],
      recurring_interview_weaknesses: [],
      average_interview_score: null,
      evaluated_sessions_count: 0,
      improvement_plan: [
        {
          skill: "Redis",
          current_gap: "Requested across 2 matched jobs.",
          priority: "high",
          action_items: ["Implement caching pattern with Redis TTLs."],
          estimated_hours: 6,
        },
      ],
    });

    const sessionDetail = {
      session: {
        id: "int-1",
        user_id: "u-1",
        job_id: null,
        application_id: null,
        title: "Junior Backend Engineer Mock Interview",
        target_role: "Junior Backend Engineer",
        company_name: "Chargebee",
        focus_area: "mixed",
        difficulty: "entry",
        status: "CREATED",
        question_count: 1,
        overall_score: null,
        created_at: "2026-11-11T12:00:00Z",
        updated_at: "2026-11-11T12:00:00Z",
      },
      questions: [
        {
          id: "q-1",
          session_id: "int-1",
          order_index: 1,
          category: "technical",
          prompt: "How do you prevent race conditions in FastAPI billing endpoints?",
          expected_topics: ["Idempotency", "Transactions"],
          difficulty: "entry",
          guidance: "Mention database transactions and idempotency keys.",
          created_at: "2026-11-11T12:00:00Z",
        },
      ],
      answers: [],
      feedback: null,
    };

    const createSpy = vi.spyOn(interviewService, "createSession").mockResolvedValue(sessionDetail);
    vi.spyOn(interviewService, "getSession").mockResolvedValue(sessionDetail);
    const ansSpy = vi.spyOn(interviewService, "submitAnswer").mockResolvedValue({
      id: "ans-1",
      question_id: "q-1",
      session_id: "int-1",
      answer_text: "Use PostgreSQL transactions and unique idempotency keys per request.",
      time_spent_seconds: null,
      submitted_at: "2026-11-11T12:01:00Z",
    });

    renderInterviewRoutes();

    await waitFor(() => {
      expect(screen.getAllByText("Redis").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Implement caching pattern with Redis TTLs.")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Target Role"), {
      target: { value: "Junior Backend Engineer" },
    });
    fireEvent.change(screen.getByLabelText("Company Name (optional)"), {
      target: { value: "Chargebee" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start Mock Interview" }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          target_role: "Junior Backend Engineer",
          company_name: "Chargebee",
        })
      );
      expect(
        screen.getByText("How do you prevent race conditions in FastAPI billing endpoints?")
      ).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Answer for question 1"), {
      target: { value: "Use PostgreSQL transactions and unique idempotency keys per request." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Answer" }));

    await waitFor(() => {
      expect(ansSpy).toHaveBeenCalledWith("int-1", {
        question_id: "q-1",
        answer_text: "Use PostgreSQL transactions and unique idempotency keys per request.",
      });
    });
  });

  it("renders rubric evaluation report on InterviewSessionPage", async () => {
    const evaluatedDetail = {
      session: {
        id: "int-2",
        user_id: "u-1",
        job_id: null,
        application_id: null,
        title: "AI Engineer Prep",
        target_role: "AI Engineer",
        company_name: null,
        focus_area: "technical",
        difficulty: "entry",
        status: "IN_PROGRESS",
        question_count: 1,
        overall_score: null,
        created_at: "2026-11-11T12:00:00Z",
        updated_at: "2026-11-11T12:00:00Z",
      },
      questions: [
        {
          id: "q-10",
          session_id: "int-2",
          order_index: 1,
          category: "technical",
          prompt: "Explain OpenCV image preprocessing pipelines.",
          expected_topics: ["Normalization"],
          difficulty: "entry",
          guidance: null,
          created_at: "2026-11-11T12:00:00Z",
        },
      ],
      answers: [
        {
          id: "ans-10",
          question_id: "q-10",
          session_id: "int-2",
          answer_text: "Resize, normalize pixel intensity, and denoise before model inference.",
          time_spent_seconds: 90,
          submitted_at: "2026-11-11T12:01:00Z",
        },
      ],
      feedback: null,
    };

    const getSpy = vi.spyOn(interviewService, "getSession").mockResolvedValue(evaluatedDetail);
    const evalSpy = vi.spyOn(interviewService, "evaluateSession").mockImplementation(async () => {
      const fb = {
        id: "fb-1",
        session_id: "int-2",
        overall_score: 86,
        rubric_scores: {
          technical_accuracy: 88,
          communication_clarity: 84,
          star_structure: 80,
          role_alignment: 90,
        },
        strengths: ["Clear explanation of OpenCV preprocessing."],
        weaknesses: ["Mention batching performance metrics."],
        question_evaluations: [],
        skill_improvement_plan: [],
        summary: "Strong computer vision fundamentals.",
        model_used: "gpt-4o-mini",
        tokens_used: 180,
        evaluated_at: "2026-11-11T12:02:00Z",
      };
      getSpy.mockResolvedValue({
        ...evaluatedDetail,
        session: { ...evaluatedDetail.session, status: "EVALUATED", overall_score: 86 },
        feedback: fb,
      });
      return fb;
    });

    renderInterviewRoutes("/interviews/int-2");

    await waitFor(() => {
      expect(screen.getByText("Explain OpenCV image preprocessing pipelines.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Evaluate with Rubric" }));

    await waitFor(() => {
      expect(evalSpy).toHaveBeenCalledWith("int-2");
      expect(screen.getByText("Evaluation Report — 86% Overall")).toBeInTheDocument();
      expect(screen.getByText("Clear explanation of OpenCV preprocessing.")).toBeInTheDocument();
    });
  });
});
