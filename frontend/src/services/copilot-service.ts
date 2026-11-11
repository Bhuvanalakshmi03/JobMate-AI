import { apiRequest } from "./api-client";
import type {
  ChatTurnResponse,
  ConversationDetailResponse,
  ConversationListResponse,
  ConversationSummary,
} from "../types/copilot";

export const copilotService = {
  listConversations: (): Promise<ConversationListResponse> =>
    apiRequest<ConversationListResponse>("/copilot/conversations", {
      timeoutMs: 30000,
    }),

  createConversation: (title?: string): Promise<ConversationSummary> =>
    apiRequest<ConversationSummary>("/copilot/conversations", {
      method: "POST",
      timeoutMs: 30000,
      body: JSON.stringify({ title: title ?? null }),
    }),

  getConversation: (conversationId: string): Promise<ConversationDetailResponse> =>
    apiRequest<ConversationDetailResponse>(`/copilot/conversations/${conversationId}`, {
      timeoutMs: 30000,
    }),

  updateConversation: (
    conversationId: string,
    payload: { title?: string; is_archived?: boolean }
  ): Promise<ConversationSummary> =>
    apiRequest<ConversationSummary>(`/copilot/conversations/${conversationId}`, {
      method: "PATCH",
      timeoutMs: 30000,
      body: JSON.stringify(payload),
    }),

  deleteConversation: (conversationId: string): Promise<void> =>
    apiRequest<void>(`/copilot/conversations/${conversationId}`, {
      method: "DELETE",
      timeoutMs: 30000,
    }),

  sendMessage: (conversationId: string, message: string): Promise<ChatTurnResponse> =>
    apiRequest<ChatTurnResponse>(`/copilot/conversations/${conversationId}/messages`, {
      method: "POST",
      timeoutMs: 120000,
      body: JSON.stringify({ message }),
    }),
};
