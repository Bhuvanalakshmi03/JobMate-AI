import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FoundationStatusPage } from "../src/features/dashboard/pages/FoundationStatusPage";
import { applicationService } from "../src/services/application-service";
import { approvalService } from "../src/services/approval-service";
import { calendarService } from "../src/services/calendar-service";
import { healthService } from "../src/services/health-service";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <FoundationStatusPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("FoundationStatusPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders backend liveness, readiness status, and application summary on success", async () => {
    vi.spyOn(healthService, "getLiveness").mockResolvedValue({
      status: "ok",
      service: "JobMate AI",
      version: "0.1.0",
      environment: "development",
      timestamp: "2026-11-10T12:00:00Z",
    });
    vi.spyOn(healthService, "getReadiness").mockResolvedValue({
      status: "ready",
      service: "JobMate AI",
      version: "0.1.0",
      environment: "development",
      timestamp: "2026-11-10T12:00:00Z",
      dependencies: {
        database: { status: "healthy", detail: null },
        redis: { status: "healthy", detail: null },
      },
    });
    vi.spyOn(applicationService, "getSummary").mockResolvedValue({
      total_applications: 4,
      counts_by_status: { PREPARING: 1, SUBMITTED: 2, INTERVIEW_SCHEDULED: 1 },
      upcoming_deadlines: [],
    });
    vi.spyOn(calendarService, "getStatus").mockResolvedValue({
      connected: false,
      google_email: null,
      scopes: [],
      token_expires_at: null,
    });
    vi.spyOn(approvalService, "listApprovals").mockResolvedValue({
      items: [],
      total: 0,
      pending_count: 0,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("JobMate AI")).toBeInTheDocument();
      expect(screen.getByText("READY")).toBeInTheDocument();
      expect(screen.getByText("Application Pipeline Summary")).toBeInTheDocument();
      expect(screen.getByText("4")).toBeInTheDocument();
    });
  });

  it("renders error state when backend fails", async () => {
    vi.spyOn(healthService, "getLiveness").mockRejectedValue(new Error("API offline"));
    vi.spyOn(healthService, "getReadiness").mockRejectedValue(new Error("API offline"));
    vi.spyOn(applicationService, "getSummary").mockRejectedValue(new Error("API offline"));
    vi.spyOn(calendarService, "getStatus").mockRejectedValue(new Error("API offline"));
    vi.spyOn(approvalService, "listApprovals").mockRejectedValue(new Error("API offline"));

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("API offline");
    });
  });
});

