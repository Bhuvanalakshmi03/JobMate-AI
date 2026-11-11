import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApprovalsPage } from "../src/features/approvals/pages/ApprovalsPage";
import { approvalService } from "../src/services/approval-service";
import type { ApprovalItem } from "../src/types/approval";

function renderApprovalsPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ApprovalsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const PENDING_ITEM: ApprovalItem = {
  id: "apr-1",
  user_id: "u-1",
  workflow_run_id: "wf-1",
  application_id: "app-1",
  action_type: "submit_application",
  target_destination: "https://careers.orbitsystems.io/backend",
  title: "Submit Application: Backend Intern at Orbit Systems",
  payload: {
    company: "Orbit Systems",
    role: "Backend Intern",
    match_score: 88.5,
  },
  status: "PENDING",
  decision_note: null,
  decided_at: null,
  executed_at: null,
  execution_result: null,
  created_at: "2026-11-11T12:00:00Z",
  updated_at: "2026-11-11T12:00:00Z",
};

describe("ApprovalsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("displays target destination & payload and executes approved actions", async () => {
    vi.spyOn(approvalService, "listApprovals").mockResolvedValue({
      items: [PENDING_ITEM],
      total: 1,
      pending_count: 1,
    });
    const approveSpy = vi.spyOn(approvalService, "approve").mockResolvedValue({
      ...PENDING_ITEM,
      status: "EXECUTED",
      decision_note: "Verified destination and documents",
      decided_at: "2026-11-11T12:05:00Z",
      executed_at: "2026-11-11T12:05:01Z",
    });

    renderApprovalsPage();

    await waitFor(() => {
      expect(
        screen.getByText("Submit Application: Backend Intern at Orbit Systems")
      ).toBeInTheDocument();
      expect(screen.getByText("https://careers.orbitsystems.io/backend")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Decision Note (optional)"), {
      target: { value: "Verified destination and documents" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Approve & Execute" }));

    await waitFor(() => {
      expect(approveSpy).toHaveBeenCalledWith("apr-1", "Verified destination and documents");
    });
  });

  it("rejects pending approval requests without executing", async () => {
    vi.spyOn(approvalService, "listApprovals").mockResolvedValue({
      items: [PENDING_ITEM],
      total: 1,
      pending_count: 1,
    });
    const rejectSpy = vi.spyOn(approvalService, "reject").mockResolvedValue({
      ...PENDING_ITEM,
      status: "REJECTED",
      decision_note: "Wrong role level",
      decided_at: "2026-11-11T12:06:00Z",
    });

    renderApprovalsPage();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Reject Action" })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Decision Note (optional)"), {
      target: { value: "Wrong role level" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reject Action" }));

    await waitFor(() => {
      expect(rejectSpy).toHaveBeenCalledWith("apr-1", "Wrong role level");
    });
  });

  it("renders error state if fetching approvals fails", async () => {
    vi.spyOn(approvalService, "listApprovals").mockRejectedValue(
      new Error("Approval service unreachable")
    );

    renderApprovalsPage();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Approval service unreachable");
    });
  });
});

