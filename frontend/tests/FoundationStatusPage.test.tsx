import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { FoundationStatusPage } from "../src/features/dashboard/pages/FoundationStatusPage";
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
  it("renders backend liveness and readiness status on success", async () => {
    vi.spyOn(healthService, "getLiveness").mockResolvedValue({
      status: "ok",
      service: "CareerPilot AI",
      version: "0.1.0",
      environment: "development",
      timestamp: "2026-11-10T12:00:00Z",
    });
    vi.spyOn(healthService, "getReadiness").mockResolvedValue({
      status: "ready",
      service: "CareerPilot AI",
      version: "0.1.0",
      environment: "development",
      timestamp: "2026-11-10T12:00:00Z",
      dependencies: {
        database: { status: "healthy", detail: null },
        redis: { status: "healthy", detail: null },
      },
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("CareerPilot AI")).toBeInTheDocument();
      expect(screen.getByText("READY")).toBeInTheDocument();
    });
  });

  it("renders error state when backend fails", async () => {
    vi.spyOn(healthService, "getLiveness").mockRejectedValue(new Error("API offline"));
    vi.spyOn(healthService, "getReadiness").mockRejectedValue(new Error("API offline"));

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("API offline");
    });
  });
});

