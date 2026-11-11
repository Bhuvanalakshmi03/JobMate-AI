export type InterviewFocusArea = "mixed" | "technical" | "behavioral" | "hr";
export type InterviewDifficulty = "entry" | "intermediate" | "senior";

export interface RubricBreakdown {
  technical_accuracy: number;
  communication_clarity: number;
  star_structure: number;
  role_alignment: number;
}

export interface QuestionEvaluationItem {
  question_id: string;
  prompt: string;
  category: string;
  score: number;
  rubric: RubricBreakdown;
  strengths: string[];
  improvements: string[];
  sample_strong_points: string[];
}

export interface SkillImprovementItem {
  skill: string;
  current_gap: string;
  priority: "high" | "medium" | "low" | string;
  action_items: string[];
  estimated_hours: number;
}

export interface InterviewQuestion {
  id: string;
  session_id: string;
  order_index: number;
  category: string;
  prompt: string;
  expected_topics: string[];
  difficulty: string;
  guidance: string | null;
  created_at: string;
}

export interface InterviewAnswer {
  id: string;
  question_id: string;
  session_id: string;
  answer_text: string;
  time_spent_seconds: number | null;
  submitted_at: string;
}

export interface InterviewFeedback {
  id: string;
  session_id: string;
  overall_score: number;
  rubric_scores: Record<string, number>;
  strengths: string[];
  weaknesses: string[];
  question_evaluations: QuestionEvaluationItem[];
  skill_improvement_plan: SkillImprovementItem[];
  summary: string;
  model_used: string | null;
  tokens_used: number;
  evaluated_at: string;
}

export interface InterviewSessionSummary {
  id: string;
  user_id: string;
  job_id: string | null;
  application_id: string | null;
  title: string;
  target_role: string;
  company_name: string | null;
  focus_area: string;
  difficulty: string;
  status: string;
  question_count: number;
  overall_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface InterviewSessionDetailResponse {
  session: InterviewSessionSummary;
  questions: InterviewQuestion[];
  answers: InterviewAnswer[];
  feedback: InterviewFeedback | null;
}

export interface InterviewSessionListResponse {
  items: InterviewSessionSummary[];
  total: number;
}

export interface InterviewCreatePayload {
  job_id?: string | null;
  application_id?: string | null;
  title?: string | null;
  target_role?: string | null;
  company_name?: string | null;
  focus_area?: InterviewFocusArea;
  difficulty?: InterviewDifficulty;
  question_count?: number;
  generate_questions?: boolean;
}

export interface SkillGapPlanResponse {
  verified_skills: string[];
  missing_skills_from_matches: string[];
  recurring_interview_weaknesses: string[];
  average_interview_score: number | null;
  evaluated_sessions_count: number;
  improvement_plan: SkillImprovementItem[];
}

export function interviewStatusTone(
  status: string
): "success" | "warning" | "info" | "neutral" {
  switch (status) {
    case "EVALUATED":
      return "success";
    case "IN_PROGRESS":
      return "warning";
    case "CREATED":
      return "info";
    default:
      return "neutral";
  }
}
