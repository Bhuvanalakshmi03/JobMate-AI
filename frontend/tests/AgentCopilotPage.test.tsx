import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AgentCopilotPage } from "../src/features/agents/pages/AgentCopilotPage";
import { agentService } from "../src/services/agent-service";
import { jobService } from "../src/services/job-service";
import { resumeService } from "../src/services/resume-service";

function renderCopilotPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
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

    fireEvent.change(screen.getByLabelText("Instruction for CareerPilot Agents"), {
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
});

