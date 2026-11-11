import { apiRequest } from "./api-client";
import type {
  ChatTurnResponse,
  ConversationDetailResponse,
  ConversationListResponse,
  ConversationSummary,
} from "../types/copilot";

export const copilotService = {
  listConversations: (): Promise<ConversationListResponse> =>
    apiRequest<ConversationListResponse>("/copilot/conversations"),

  createConversation: (title?: string): Promise<ConversationSummary> =>
    apiRequest<ConversationSummary>("/copilot/conversations", {
      method: "POST",
      body: JSON.stringify({ title: title ?? null }),
    }),

  getConversation: (conversationId: string): Promise<ConversationDetailResponse> =>
    apiRequest<ConversationDetailResponse>(`/copilot/conversations/${conversationId}`),

  updateConversation: (
    conversationId: string,
    payload: { title?: string; is_archived?: boolean }
  ): Promise<ConversationSummary> =>
    apiRequest<ConversationSummary>(`/copilot/conversations/${conversationId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteConversation: (conversationId: string): Promise<void> =>
    apiRequest<void>(`/copilot/conversations/${conversationId}`, {
      method: "DELETE",
    }),

  sendMessage: (conversationId: string, message: string): Promise<ChatTurnResponse> =>
    apiRequest<ChatTurnResponse>(`/copilot/conversations/${conversationId}/messages`, {
      method: "POST",
      timeoutMs: 120000,
      body: JSON.stringify({ message }),
    }),
};
