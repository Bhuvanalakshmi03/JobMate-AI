import { apiRequest } from "./api-client";
import type {
  InterviewAnswer,
  InterviewCreatePayload,
  InterviewFeedback,
  InterviewFocusArea,
  InterviewQuestion,
  InterviewSessionDetailResponse,
  InterviewSessionListResponse,
  SkillGapPlanResponse,
} from "../types/interview";

export const interviewService = {
  listSessions: (status?: string): Promise<InterviewSessionListResponse> =>
    apiRequest<InterviewSessionListResponse>(
      status ? `/interviews?status=${encodeURIComponent(status)}` : "/interviews"
    ),

  createSession: (payload: InterviewCreatePayload): Promise<InterviewSessionDetailResponse> =>
    apiRequest<InterviewSessionDetailResponse>("/interviews", {
      method: "POST",
      timeoutMs: 90000,
      body: JSON.stringify(payload),
    }),

  getSession: (sessionId: string): Promise<InterviewSessionDetailResponse> =>
    apiRequest<InterviewSessionDetailResponse>(`/interviews/${sessionId}`),

  deleteSession: (sessionId: string): Promise<void> =>
    apiRequest<void>(`/interviews/${sessionId}`, {
      method: "DELETE",
    }),

  generateQuestions: (
    sessionId: string,
    payload: { count?: number; focus_area?: InterviewFocusArea | null }
  ): Promise<InterviewQuestion[]> =>
    apiRequest<InterviewQuestion[]>(`/interviews/${sessionId}/questions`, {
      method: "POST",
      timeoutMs: 90000,
      body: JSON.stringify(payload),
    }),

  submitAnswer: (
    sessionId: string,
    payload: { question_id: string; answer_text: string; time_spent_seconds?: number | null }
  ): Promise<InterviewAnswer> =>
    apiRequest<InterviewAnswer>(`/interviews/${sessionId}/answers`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  evaluateSession: (sessionId: string): Promise<InterviewFeedback> =>
    apiRequest<InterviewFeedback>(`/interviews/${sessionId}/evaluate`, {
      method: "POST",
      timeoutMs: 90000,
    }),

  getFeedback: (sessionId: string): Promise<InterviewFeedback> =>
    apiRequest<InterviewFeedback>(`/interviews/${sessionId}/feedback`),

  getSkillGapPlan: (): Promise<SkillGapPlanResponse> =>
    apiRequest<SkillGapPlanResponse>("/interviews/skill-gap-plan"),
};
