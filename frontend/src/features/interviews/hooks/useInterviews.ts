import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { interviewService } from "../../../services/interview-service";
import type { InterviewCreatePayload, InterviewFocusArea } from "../../../types/interview";

export function useInterviewSessionsList(status?: string) {
  return useQuery({
    queryKey: ["interviews", "list", status ?? "all"],
    queryFn: () => interviewService.listSessions(status || undefined),
    retry: false,
  });
}

export function useInterviewDetail(sessionId: string) {
  return useQuery({
    queryKey: ["interviews", "detail", sessionId],
    queryFn: () => interviewService.getSession(sessionId),
    enabled: Boolean(sessionId),
    retry: false,
  });
}

export function useSkillGapPlan() {
  return useQuery({
    queryKey: ["interviews", "skill-gap-plan"],
    queryFn: interviewService.getSkillGapPlan,
    retry: false,
  });
}

export function useCreateInterviewMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: InterviewCreatePayload) => interviewService.createSession(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["interviews"] });
    },
  });
}

export function useGenerateQuestionsMutation(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { count?: number; focus_area?: InterviewFocusArea | null }) =>
      interviewService.generateQuestions(sessionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["interviews", "detail", sessionId] });
      void queryClient.invalidateQueries({ queryKey: ["interviews", "list"] });
    },
  });
}

export function useSubmitAnswerMutation(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      question_id: string;
      answer_text: string;
      time_spent_seconds?: number | null;
    }) => interviewService.submitAnswer(sessionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["interviews", "detail", sessionId] });
      void queryClient.invalidateQueries({ queryKey: ["interviews", "list"] });
    },
  });
}

export function useEvaluateInterviewMutation(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => interviewService.evaluateSession(sessionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["interviews"] });
    },
  });
}

export function useDeleteInterviewMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => interviewService.deleteSession(sessionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["interviews"] });
    },
  });
}
