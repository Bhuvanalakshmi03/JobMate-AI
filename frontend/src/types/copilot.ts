import type { ApprovalItem } from "./approval";

export interface ToolExecutionLog {
  tool_name: string;
  arguments: Record<string, unknown>;
  status: string;
  result_preview: string;
}

export interface ConversationSummary {
  id: string;
  user_id: string;
  title: string;
  is_archived: boolean;
  last_message_at: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  items: ConversationSummary[];
  total: number;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | string;
  content: string;
  tool_calls: ToolExecutionLog[];
  approval_ids: string[];
  tokens_used: number;
  created_at: string;
}

export interface ConversationDetailResponse {
  conversation: ConversationSummary;
  messages: ChatMessage[];
  approvals: ApprovalItem[];
}

export interface ChatTurnResponse {
  conversation: ConversationSummary;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  created_approvals: ApprovalItem[];
}
