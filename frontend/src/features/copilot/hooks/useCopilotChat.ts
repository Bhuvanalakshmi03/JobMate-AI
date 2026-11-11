import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { copilotService } from "../../../services/copilot-service";

export function useConversationsList() {
  return useQuery({
    queryKey: ["copilot", "conversations"],
    queryFn: copilotService.listConversations,
    retry: false,
  });
}

export function useConversationDetail(conversationId: string) {
  return useQuery({
    queryKey: ["copilot", "conversation", conversationId],
    queryFn: () => copilotService.getConversation(conversationId),
    enabled: Boolean(conversationId),
    retry: false,
  });
}

export function useCreateConversationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (title?: string) => copilotService.createConversation(title),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["copilot", "conversations"] });
    },
  });
}

export function useUpdateConversationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { conversationId: string; title?: string; is_archived?: boolean }) =>
      copilotService.updateConversation(params.conversationId, {
        title: params.title,
        is_archived: params.is_archived,
      }),
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({ queryKey: ["copilot", "conversations"] });
      void queryClient.invalidateQueries({
        queryKey: ["copilot", "conversation", vars.conversationId],
      });
    },
  });
}

export function useDeleteConversationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) => copilotService.deleteConversation(conversationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["copilot", "conversations"] });
    },
  });
}

export function useSendMessageMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { conversationId: string; message: string }) =>
      copilotService.sendMessage(params.conversationId, params.message),
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({ queryKey: ["copilot", "conversations"] });
      void queryClient.invalidateQueries({
        queryKey: ["copilot", "conversation", vars.conversationId],
      });
      void queryClient.invalidateQueries({ queryKey: ["approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["profile"] });
      void queryClient.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}
