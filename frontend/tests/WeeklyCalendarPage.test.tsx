import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WeeklyCalendarPage } from "../src/features/calendar/pages/WeeklyCalendarPage";
import { approvalService } from "../src/services/approval-service";
import { calendarService } from "../src/services/calendar-service";

function renderWeeklyCalendarPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/calendar"]}>
        <WeeklyCalendarPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("WeeklyCalendarPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("displays all scheduled events within 1 week and allows adding a new event", async () => {
    vi.spyOn(calendarService, "getStatus").mockResolvedValue({
      connected: true,
      google_email: "mukilan069@gmail.com",
      scopes: ["https://www.googleapis.com/auth/calendar.events"],
      token_expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
    });

    const tomorrowStart = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    const tomorrowEnd = new Date(Date.now() + 24 * 60 * 60 * 1000 + 3600 * 1000).toISOString();
    const tenDaysStart = new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString();
    const tenDaysEnd = new Date(Date.now() + 10 * 24 * 60 * 60 * 1000 + 3600 * 1000).toISOString();

    vi.spyOn(calendarService, "listEvents").mockResolvedValue({
      connected: true,
      items: [
        {
          event_id: "evt-in-week",
          summary: "Freshworks Technical Round",
          start_iso: tomorrowStart,
          end_iso: tomorrowEnd,
          location: "Google Meet",
          description: "Live Python & React screening",
          html_link: "https://calendar.google.com/event?eid=freshworks",
          status: "confirmed",
        },
        {
          event_id: "evt-outside-week",
          summary: "Next Month Career Fair",
          start_iso: tenDaysStart,
          end_iso: tenDaysEnd,
          location: null,
          description: null,
          html_link: null,
          status: "confirmed",
        },
      ],
    });

    vi.spyOn(approvalService, "listApprovals").mockResolvedValue({
      items: [],
      total: 0,
      pending_count: 0,
    });

    const createSpy = vi.spyOn(calendarService, "createEvent").mockResolvedValue({
      event_id: "evt-new",
      summary: "Mock System Design Block",
      start_iso: tomorrowStart,
      end_iso: tomorrowEnd,
      location: "Home Desk",
      description: null,
      html_link: null,
      status: "confirmed",
    });

    renderWeeklyCalendarPage();

    await waitFor(() => {
      expect(screen.getByText("Freshworks Technical Round")).toBeInTheDocument();
      expect(screen.getByText("Google Meet")).toBeInTheDocument();
    });
    expect(screen.queryByText("Next Month Career Fair")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Add Event" }));
    fireEvent.change(screen.getByLabelText("Event Title"), {
      target: { value: "Mock System Design Block" },
    });
    fireEvent.change(screen.getByLabelText("Location (optional)"), {
      target: { value: "Home Desk" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save to Google Calendar" }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          summary: "Mock System Design Block",
          location: "Home Desk",
        })
      );
    });
  });
});
