import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AgentCopilotPage } from "../src/features/agents/pages/AgentCopilotPage";
import { agentService } from "../src/services/agent-service";
import { approvalService } from "../src/services/approval-service";
import { calendarService } from "../src/services/calendar-service";
import { copilotService } from "../src/services/copilot-service";
import { jobService } from "../src/services/job-service";
import { resumeService } from "../src/services/resume-service";

function renderCopilotPage(initialRoute = "/copilot") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <AgentCopilotPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("AgentCopilotPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("syncs knowledge to ChromaDB, queries RAG context, and runs a LangGraph workflow", async () => {
    vi.spyOn(jobService, "searchJobs").mockResolvedValue({
      items: [],
      total: 0,
      source: "database",
      cached: false,
    });
    vi.spyOn(resumeService, "listResumes").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(agentService, "listWorkflows").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(copilotService, "listConversations").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(approvalService, "listApprovals").mockResolvedValue({
      items: [],
      total: 0,
      pending_count: 0,
    });
    vi.spyOn(calendarService, "getStatus").mockResolvedValue({
      connected: false,
      google_email: null,
      scopes: [],
      token_expires_at: null,
    });

    const syncSpy = vi.spyOn(agentService, "syncRag").mockResolvedValue({
      indexed_chunks: 4,
      skipped_duplicates: 0,
      source_counts: { profile: 1, resume_fact: 3, document: 0 },
    });
    const ragSpy = vi.spyOn(agentService, "queryRag").mockResolvedValue({
      query: "FastAPI backend",
      hits: [
        {
          chunk_id: "c-1",
          score: 0.91,
          source_type: "resume_fact",
          label: "API Engineering",
          text: "Built FastAPI services with async PostgreSQL.",
        },
      ],
    });
    const startSpy = vi.spyOn(agentService, "startWorkflow").mockResolvedValue({
      id: "wf-1",
      user_id: "u-1",
      job_id: "job-1",
      application_id: "app-1",
      task_type: "application_prep",
      user_request: "Prepare tailored resume and approval for Backend Intern",
      current_stage: "awaiting_human_approval",
      status: "PAUSED_FOR_APPROVAL",
      agent_outputs: { job_matcher: { overall_score: 88.5 } },
      validation_results: { documents_grounded: true },
      pending_approval_id: "apr-1",
      execution_trace: [
        {
          node: "request_validator",
          status: "completed",
          attempts: 1,
          duration_ms: 2.4,
          tokens_used: 0,
          detail: "Validated request",
          timestamp: "2026-11-11T12:00:00Z",
        },
        {
          node: "approval_gate",
          status: "completed",
          attempts: 1,
          duration_ms: 4.2,
          tokens_used: 0,
          detail: "Paused for user confirmation",
          timestamp: "2026-11-11T12:00:01Z",
        },
      ],
      total_tokens_used: 210,
      error_detail: null,
      created_at: "2026-11-11T12:00:00Z",
      updated_at: "2026-11-11T12:00:01Z",
    });

    renderCopilotPage();

    fireEvent.click(screen.getByRole("tab", { name: /LangGraph Workflows & RAG/i }));

    fireEvent.click(screen.getByRole("button", { name: "Sync Knowledge to ChromaDB" }));
    await waitFor(() => {
      expect(syncSpy).toHaveBeenCalled();
      expect(screen.getByText(/Indexed 4 chunk\(s\)/)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Query career context"), {
      target: { value: "FastAPI backend" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Retrieve RAG Context" }));
    await waitFor(() => {
      expect(ragSpy).toHaveBeenCalledWith({ query: "FastAPI backend", top_k: 5 });
      expect(screen.getByText("API Engineering")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Instruction for JobMate AI Agents"), {
      target: { value: "Prepare tailored resume and approval for Backend Intern" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run Co-Pilot Workflow" }));

    await waitFor(() => {
      expect(startSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          requested_task: "Prepare tailored resume and approval for Backend Intern",
        })
      );
      expect(screen.getByText("Paused at Human Approval Gate")).toBeInTheDocument();
      expect(screen.getByText("approval_gate")).toBeInTheDocument();
    });
  });

  it("manages Co-Pilot chat sessions, renders tool calls, and executes approved Google Calendar events", async () => {
    vi.spyOn(jobService, "searchJobs").mockResolvedValue({
      items: [],
      total: 0,
      source: "database",
      cached: false,
    });
    vi.spyOn(resumeService, "listResumes").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(agentService, "listWorkflows").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(approvalService, "listApprovals").mockResolvedValue({
      items: [],
      total: 0,
      pending_count: 0,
    });
    vi.spyOn(calendarService, "getStatus").mockResolvedValue({
      connected: true,
      google_email: "mukilan069@gmail.com",
      scopes: ["https://www.googleapis.com/auth/calendar.events"],
      token_expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
    });
    const inWeekStart = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    const inWeekEnd = new Date(Date.now() + 24 * 60 * 60 * 1000 + 45 * 60 * 1000).toISOString();
    const outWeekStart = new Date(Date.now() + 12 * 24 * 60 * 60 * 1000).toISOString();
    const outWeekEnd = new Date(Date.now() + 12 * 24 * 60 * 60 * 1000 + 45 * 60 * 1000).toISOString();
    const listEventsSpy = vi.spyOn(calendarService, "listEvents").mockResolvedValue({
      connected: true,
      items: [
        {
          event_id: "evt-1",
          summary: "Mock System Design Review",
          start_iso: inWeekStart,
          end_iso: inWeekEnd,
          location: "Google Meet",
          description: null,
          html_link: "https://calendar.google.com/event?eid=evt-1",
          status: "confirmed",
        },
        {
          event_id: "evt-far",
          summary: "Two Weeks Out Workshop",
          start_iso: outWeekStart,
          end_iso: outWeekEnd,
          location: null,
          description: null,
          html_link: null,
          status: "confirmed",
        },
      ],
    });

    const convSummary = {
      id: "conv-1",
      user_id: "u-1",
      title: "Zoho Prep Session",
      is_archived: false,
      last_message_at: "2026-11-11T12:00:00Z",
      created_at: "2026-11-11T11:50:00Z",
      updated_at: "2026-11-11T12:00:00Z",
    };

    const approvalItem = {
      id: "apr-cal-1",
      user_id: "u-1",
      workflow_run_id: null,
      application_id: null,
      action_type: "create_calendar_event",
      target_destination: "Google Calendar (primary)",
      title: "Add Calendar Event: Zoho Interview Prep",
      payload: { summary: "Zoho Interview Prep" },
      status: "PENDING",
      decision_note: null,
      decided_at: null,
      executed_at: null,
      execution_result: null,
      created_at: "2026-11-11T12:00:00Z",
      updated_at: "2026-11-11T12:00:00Z",
    };

    vi.spyOn(copilotService, "listConversations").mockResolvedValue({
      items: [convSummary],
      total: 1,
    });
    vi.spyOn(copilotService, "getConversation").mockResolvedValue({
      conversation: convSummary,
      messages: [
        {
          id: "msg-1",
          conversation_id: "conv-1",
          role: "assistant",
          content: "I checked your schedule and staged the Zoho prep calendar block for approval.",
          tool_calls: [
            {
              tool_name: "list_calendar_events",
              arguments: { days_ahead: 7 },
              status: "completed",
              result_preview: "Found 1 upcoming event",
            },
          ],
          approval_ids: ["apr-cal-1"],
          tokens_used: 95,
          created_at: "2026-11-11T12:00:00Z",
        },
      ],
      approvals: [approvalItem],
    });

    const sendSpy = vi.spyOn(copilotService, "sendMessage").mockResolvedValue({
      conversation: convSummary,
      user_message: {
        id: "msg-2",
        conversation_id: "conv-1",
        role: "user",
        content: "Add a follow-up note for Chargebee",
        tool_calls: [],
        approval_ids: [],
        tokens_used: 0,
        created_at: "2026-11-11T12:01:00Z",
      },
      assistant_message: {
        id: "msg-3",
        conversation_id: "conv-1",
        role: "assistant",
        content: "Updated Chargebee notes.",
        tool_calls: [],
        approval_ids: [],
        tokens_used: 40,
        created_at: "2026-11-11T12:01:02Z",
      },
      created_approvals: [],
    });

    const approveSpy = vi.spyOn(approvalService, "approve").mockResolvedValue({
      ...approvalItem,
      status: "EXECUTED",
    });

    renderCopilotPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Zoho Prep Session" })).toBeInTheDocument();
      expect(listEventsSpy).toHaveBeenCalledWith(7, 50);
      expect(screen.getByText("Mock System Design Review")).toBeInTheDocument();
      expect(screen.queryByText("Two Weeks Out Workshop")).not.toBeInTheDocument();
      expect(screen.getByText(/list_calendar_events \(completed\)/)).toBeInTheDocument();
      expect(screen.getByText("Add Calendar Event: Zoho Interview Prep")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Approve & Execute" }));
    await waitFor(() => {
      expect(approveSpy).toHaveBeenCalledWith("apr-cal-1", "Approved from Co-Pilot Chat");
    });

    fireEvent.change(screen.getByLabelText("Message AI Co-Pilot"), {
      target: { value: "Add a follow-up note for Chargebee" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(sendSpy).toHaveBeenCalledWith("conv-1", "Add a follow-up note for Chargebee");
    });
  });
});
