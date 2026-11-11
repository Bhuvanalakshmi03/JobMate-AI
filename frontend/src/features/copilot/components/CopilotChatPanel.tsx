import {
  CalendarPlus,
  Check,
  Edit3,
  MessageSquarePlus,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  Wrench,
  X,
} from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  approvalActionLabel,
  approvalStatusTone,
  type ApprovalItem,
} from "../../../types/approval";
import { formatDisplayDate } from "../../applications/utils/dates";
import {
  useApproveActionMutation,
  useRejectActionMutation,
} from "../../approvals/hooks/useApprovals";
import { WeeklyCalendarCard } from "../../calendar/components/WeeklyCalendarCard";
import {
  useConversationDetail,
  useConversationsList,
  useCreateConversationMutation,
  useDeleteConversationMutation,
  useSendMessageMutation,
  useUpdateConversationMutation,
} from "../hooks/useCopilotChat";

const STARTER_PROMPTS = [
  "Summarize my active applications, top job matches, and pending approvals",
  "Check my upcoming Google Calendar schedule for the next 7 days",
  "Propose a 45-minute technical interview prep block on Google Calendar for Friday 4 PM IST",
  "Prepare a tailored cover letter and submission request for Freshworks",
];

interface CopilotChatPanelProps {
  calendarJustConnected?: boolean;
}

export function CopilotChatPanel({ calendarJustConnected = false }: CopilotChatPanelProps) {
  const conversationsQuery = useConversationsList();
  const conversations = conversationsQuery.data?.items ?? [];

  const [selectedConversationId, setSelectedConversationId] = useState<string>("");
  const [draftMessage, setDraftMessage] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [chatError, setChatError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedConversationId && conversations.length > 0) {
      setSelectedConversationId(conversations[0].id);
    } else if (
      selectedConversationId &&
      conversations.length > 0 &&
      !conversations.some((c) => c.id === selectedConversationId)
    ) {
      setSelectedConversationId(conversations[0].id);
    }
  }, [conversations, selectedConversationId]);

  const detailQuery = useConversationDetail(selectedConversationId);
  const createConversationMutation = useCreateConversationMutation();
  const updateConversationMutation = useUpdateConversationMutation();
  const deleteConversationMutation = useDeleteConversationMutation();
  const sendMessageMutation = useSendMessageMutation();

  const approveMutation = useApproveActionMutation();
  const rejectMutation = useRejectActionMutation();

  const activeConversation = detailQuery.data?.conversation;
  const messages = detailQuery.data?.messages ?? [];
  const approvalsById = new Map<string, ApprovalItem>(
    (detailQuery.data?.approvals ?? []).map((item) => [item.id, item])
  );

  const handleCreateSession = async () => {
    setChatError(null);
    try {
      const created = await createConversationMutation.mutateAsync(undefined);
      setSelectedConversationId(created.id);
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Failed to create chat session.");
    }
  };

  const handleDeleteSession = async (conversationId: string) => {
    setChatError(null);
    try {
      await deleteConversationMutation.mutateAsync(conversationId);
      if (selectedConversationId === conversationId) {
        setSelectedConversationId("");
      }
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Failed to delete session.");
    }
  };

  const handleSaveRename = async (conversationId: string) => {
    const trimmed = editingTitle.trim();
    if (!trimmed) {
      setEditingId(null);
      return;
    }
    try {
      await updateConversationMutation.mutateAsync({ conversationId, title: trimmed });
      setEditingId(null);
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Failed to rename session.");
    }
  };

  const handleSendText = async (textToSend: string) => {
    const trimmed = textToSend.trim();
    if (!trimmed || sendMessageMutation.isPending) return;
    setChatError(null);
    try {
      let targetConversationId = selectedConversationId;
      if (!targetConversationId) {
        const created = await createConversationMutation.mutateAsync(undefined);
        targetConversationId = created.id;
        setSelectedConversationId(created.id);
      }
      setDraftMessage("");
      await sendMessageMutation.mutateAsync({
        conversationId: targetConversationId,
        message: trimmed,
      });
    } catch (err) {
      setDraftMessage(trimmed);
      setChatError(err instanceof Error ? err.message : "Co-Pilot chat request failed.");
    }
  };

  const handleFormSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await handleSendText(draftMessage);
  };

  return (
    <div className="space-y-4">
      {calendarJustConnected && (
        <StateNotice
          title="Google Calendar connected"
          description="AI Co-Pilot can now inspect your upcoming events and propose new interviews or study reminders (always gated by your approval)."
          tone="info"
        />
      )}

      {chatError && (
        <StateNotice title="Co-Pilot action notice" description={chatError} tone="error" />
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Sidebar: Sessions & Google Calendar */}
        <div className="space-y-5 lg:col-span-4">
          <Card
            title="Chat Sessions"
            subtitle={`${conversations.length} persistent session(s)`}
            action={
              <button
                type="button"
                onClick={() => void handleCreateSession()}
                disabled={createConversationMutation.isPending}
                className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                <MessageSquarePlus className="h-3.5 w-3.5" aria-hidden="true" />
                New Chat
              </button>
            }
          >
            {conversationsQuery.isPending ? (
              <p className="text-xs text-slate-500">Loading chat sessions...</p>
            ) : conversations.length === 0 ? (
              <p className="text-xs text-slate-500">
                No conversations yet. Click New Chat or send a message below to start one.
              </p>
            ) : (
              <ul className="space-y-2">
                {conversations.map((conv) => {
                  const isActive = conv.id === selectedConversationId;
                  const isEditing = editingId === conv.id;
                  return (
                    <li
                      key={conv.id}
                      className={`rounded-lg border p-2.5 transition-colors ${
                        isActive
                          ? "border-indigo-300 bg-indigo-50/70"
                          : "border-slate-200 bg-white hover:bg-slate-50"
                      }`}
                    >
                      {isEditing ? (
                        <div className="flex items-center gap-1.5">
                          <input
                            type="text"
                            aria-label="Rename conversation title"
                            value={editingTitle}
                            onChange={(e) => setEditingTitle(e.target.value)}
                            className="w-full rounded border border-indigo-300 px-2 py-1 text-xs focus:outline-none"
                          />
                          <button
                            type="button"
                            aria-label="Save title"
                            onClick={() => void handleSaveRename(conv.id)}
                            className="rounded p-1 text-emerald-700 hover:bg-emerald-50"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            aria-label="Cancel rename"
                            onClick={() => setEditingId(null)}
                            className="rounded p-1 text-slate-500 hover:bg-slate-100"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-start justify-between gap-2">
                          <button
                            type="button"
                            onClick={() => setSelectedConversationId(conv.id)}
                            className="min-w-0 flex-1 text-left"
                          >
                            <p className="truncate text-xs font-semibold text-slate-900">
                              {conv.title}
                            </p>
                            <p className="mt-0.5 text-[11px] text-slate-400">
                              {formatDisplayDate(conv.last_message_at)}
                            </p>
                          </button>
                          <div className="flex shrink-0 items-center gap-1">
                            <button
                              type="button"
                              aria-label={`Rename ${conv.title}`}
                              onClick={() => {
                                setEditingId(conv.id);
                                setEditingTitle(conv.title);
                              }}
                              className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                            >
                              <Edit3 className="h-3.5 w-3.5" />
                            </button>
                            <button
                              type="button"
                              aria-label={`Delete ${conv.title}`}
                              onClick={() => void handleDeleteSession(conv.id)}
                              className="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>

          <WeeklyCalendarCard compact redirectTo="/copilot" />
        </div>

        {/* Main Chat Transcript & Tool Execution Window */}
        <div className="lg:col-span-8">
          <Card
            title={activeConversation?.title ?? "JobMate AI Co-Pilot Chat"}
            subtitle="OpenAI function calling across Profile, Jobs, Matches, Documents, Applications, Approvals & Google Calendar"
          >
            <div className="flex min-h-[460px] flex-col justify-between gap-4">
              <div className="max-h-[540px] space-y-4 overflow-y-auto pr-1">
                {messages.length === 0 ? (
                  <div className="space-y-4 rounded-xl border border-dashed border-slate-200 bg-slate-50/70 p-5">
                    <div className="flex items-start gap-3">
                      <Sparkles className="mt-0.5 h-5 w-5 text-indigo-600" aria-hidden="true" />
                      <div>
                        <p className="text-sm font-semibold text-slate-900">
                          Control JobMate AI through natural conversation
                        </p>
                        <p className="mt-1 text-xs text-slate-600">
                          Ask Co-Pilot to search jobs, inspect your match score, update tracked
                          applications, generate grounded documents, inspect Google Calendar, or
                          stage human-approved calendar/submission actions.
                        </p>
                      </div>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {STARTER_PROMPTS.map((prompt) => (
                        <button
                          key={prompt}
                          type="button"
                          onClick={() => void handleSendText(prompt)}
                          className="rounded-lg border border-slate-200 bg-white p-2.5 text-left text-xs font-medium text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50/40"
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  messages.map((msg) => {
                    const isUser = msg.role === "user";
                    const linkedApprovals = msg.approval_ids
                      .map((id) => approvalsById.get(id))
                      .filter((item): item is ApprovalItem => Boolean(item));

                    return (
                      <div
                        key={msg.id}
                        className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
                      >
                        <div
                          className={`max-w-[92%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                            isUser
                              ? "bg-indigo-600 text-white"
                              : "border border-slate-200 bg-slate-50 text-slate-800"
                          }`}
                        >
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        </div>

                        {!isUser && msg.tool_calls.length > 0 && (
                          <div className="mt-2 flex max-w-[92%] flex-wrap gap-1.5">
                            {msg.tool_calls.map((tc, idx) => (
                              <span
                                key={`${msg.id}-tool-${idx}`}
                                title={tc.result_preview}
                                className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-[11px] font-medium text-indigo-800"
                              >
                                <Wrench className="h-3 w-3" aria-hidden="true" />
                                {tc.tool_name} ({tc.status})
                              </span>
                            ))}
                          </div>
                        )}

                        {!isUser && linkedApprovals.length > 0 && (
                          <div className="mt-2.5 w-full max-w-[92%] space-y-2">
                            {linkedApprovals.map((approval) => {
                              const isPending = approval.status === "PENDING";
                              return (
                                <div
                                  key={approval.id}
                                  className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-xs"
                                >
                                  <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div className="flex items-center gap-1.5 font-semibold text-slate-900">
                                      {approval.action_type === "create_calendar_event" ? (
                                        <CalendarPlus
                                          className="h-4 w-4 text-amber-700"
                                          aria-hidden="true"
                                        />
                                      ) : (
                                        <ShieldCheck
                                          className="h-4 w-4 text-amber-700"
                                          aria-hidden="true"
                                        />
                                      )}
                                      <span>{approval.title}</span>
                                    </div>
                                    <StatusBadge
                                      label={approval.status}
                                      tone={approvalStatusTone(approval.status)}
                                    />
                                  </div>
                                  <p className="mt-1 text-[11px] text-slate-600">
                                    Action: <strong>{approvalActionLabel(approval.action_type)}</strong> ·
                                    Target: {approval.target_destination}
                                  </p>
                                  {isPending && (
                                    <div className="mt-2.5 flex items-center gap-2">
                                      <button
                                        type="button"
                                        disabled={
                                          approveMutation.isPending || rejectMutation.isPending
                                        }
                                        onClick={() =>
                                          void approveMutation.mutateAsync({
                                            approvalId: approval.id,
                                            note: "Approved from Co-Pilot Chat",
                                          })
                                        }
                                        className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                                      >
                                        Approve & Execute
                                      </button>
                                      <button
                                        type="button"
                                        disabled={
                                          approveMutation.isPending || rejectMutation.isPending
                                        }
                                        onClick={() =>
                                          void rejectMutation.mutateAsync({
                                            approvalId: approval.id,
                                            note: "Rejected from Co-Pilot Chat",
                                          })
                                        }
                                        className="rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                                      >
                                        Reject
                                      </button>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}

                        <span className="mt-1 text-[10px] text-slate-400">
                          {formatDisplayDate(msg.created_at)}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>

              <form onSubmit={(e) => void handleFormSubmit(e)} className="border-t border-slate-200 pt-3">
                <label htmlFor="copilot-chat-input" className="sr-only">
                  Message AI Co-Pilot
                </label>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    id="copilot-chat-input"
                    type="text"
                    value={draftMessage}
                    onChange={(e) => setDraftMessage(e.target.value)}
                    placeholder="Ask Co-Pilot to search jobs, check Calendar, propose an event, track applications..."
                    className="flex-1 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:border-indigo-500 focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={sendMessageMutation.isPending || !draftMessage.trim()}
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    <Send className="h-4 w-4" aria-hidden="true" />
                    {sendMessageMutation.isPending ? "Running Tools..." : "Send"}
                  </button>
                </div>
              </form>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

