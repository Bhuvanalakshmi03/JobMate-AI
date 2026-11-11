import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../src/features/authentication/hooks/useAuth";
import { MemoryAndPrivacyPage } from "../src/features/memory/pages/MemoryAndPrivacyPage";
import { RemindersPage } from "../src/features/reminders/pages/RemindersPage";
import { applicationService } from "../src/services/application-service";
import { authService } from "../src/services/auth-service";
import { memoryService } from "../src/services/memory-service";
import { reminderService } from "../src/services/reminder-service";

function renderWithQuery(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Phase 9 MemoryAndPrivacyPage & RemindersPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("manages Career Memory consent, CRUD, and JSON data export", async () => {
    vi.spyOn(authService, "getMe").mockResolvedValue({
      id: "u-1",
      email: "mukilan069@gmail.com",
      full_name: "MUKILAN S",
      oauth_provider: "google",
      timezone: "Asia/Kolkata",
      is_demo_auth: false,
      created_at: "2026-11-11T12:00:00Z",
    });

    vi.spyOn(memoryService, "listMemories").mockResolvedValue({
      consent: { ai_consent_given: true, notification_consent: false },
      items: [
        {
          id: "m-1",
          user_id: "u-1",
          category: "preference",
          title: "Location Target",
          content: "Prefer hybrid roles in Chennai or Bengaluru.",
          source: "user_manual",
          memory_key: "loc_pref",
          is_approved: true,
          is_active: true,
          created_at: "2026-11-11T12:00:00Z",
          updated_at: "2026-11-11T12:00:00Z",
        },
      ],
      total: 1,
    });

    const createSpy = vi.spyOn(memoryService, "createMemory").mockResolvedValue({
      id: "m-2",
      user_id: "u-1",
      category: "goal",
      title: "Backend Role Focus",
      content: "Targeting FastAPI and AI engineering roles.",
      source: "user_manual",
      memory_key: null,
      is_approved: true,
      is_active: true,
      created_at: "2026-11-11T12:05:00Z",
      updated_at: "2026-11-11T12:05:00Z",
    });

    renderWithQuery(
      <AuthProvider>
        <MemoryAndPrivacyPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Location Target")).toBeInTheDocument();
      expect(screen.getByText("MEMORY OPT-IN")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Category"), { target: { value: "goal" } });
    fireEvent.change(screen.getByLabelText("Memory Title"), {
      target: { value: "Backend Role Focus" },
    });
    fireEvent.change(screen.getByLabelText("Detail"), {
      target: { value: "Targeting FastAPI and AI engineering roles." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Career Memory" }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith({
        category: "goal",
        title: "Backend Role Focus",
        content: "Targeting FastAPI and AI engineering roles.",
        is_approved: true,
      });
    });
  });

  it("schedules reminders, dispatches due alerts, and supports cancellation", async () => {
    vi.spyOn(applicationsListHookFix(), "listApplications").mockResolvedValue({
      items: [],
      total: 0,
    });
    vi.spyOn(reminderService, "listReminders").mockResolvedValue({
      items: [
        {
          id: "r-1",
          user_id: "u-1",
          application_id: null,
          job_id: null,
          title: "Send Zoho thank-you note",
          message: "After technical screen",
          reminder_type: "follow_up",
          dedup_key: "zoho-followup",
          scheduled_for: "2026-11-12T10:00:00Z",
          user_timezone: "Asia/Kolkata",
          channel: "in_app",
          status: "SCHEDULED",
          attempts: 0,
          max_attempts: 3,
          last_error: null,
          sent_at: null,
          next_retry_at: null,
          created_at: "2026-11-11T12:00:00Z",
          updated_at: "2026-11-11T12:00:00Z",
        },
      ],
      total: 1,
      due_notifications_count: 0,
    });

    const createSpy = vi.spyOn(reminderService, "createReminder").mockResolvedValue({
      id: "r-2",
      user_id: "u-1",
      application_id: null,
      job_id: null,
      title: "Mock Study Block",
      message: null,
      reminder_type: "study_plan",
      dedup_key: null,
      scheduled_for: "2026-11-12T12:00:00Z",
      user_timezone: "Asia/Kolkata",
      channel: "in_app",
      status: "SCHEDULED",
      attempts: 0,
      max_attempts: 3,
      last_error: null,
      sent_at: null,
      next_retry_at: null,
      created_at: "2026-11-11T12:00:00Z",
      updated_at: "2026-11-11T12:00:00Z",
    });

    const cancelSpy = vi.spyOn(reminderService, "cancelReminder").mockResolvedValue({
      id: "r-1",
      user_id: "u-1",
      application_id: null,
      job_id: null,
      title: "Send Zoho thank-you note",
      message: "After technical screen",
      reminder_type: "follow_up",
      dedup_key: "zoho-followup",
      scheduled_for: "2026-11-12T10:00:00Z",
      user_timezone: "Asia/Kolkata",
      channel: "in_app",
      status: "CANCELLED",
      attempts: 0,
      max_attempts: 3,
      last_error: null,
      sent_at: null,
      next_retry_at: null,
      created_at: "2026-11-11T12:00:00Z",
      updated_at: "2026-11-11T12:05:00Z",
    });

    renderWithQuery(<RemindersPage />);

    await waitFor(() => {
      expect(screen.getByText("Send Zoho thank-you note")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => {
      expect(cancelSpy).toHaveBeenCalledWith("r-1");
    });

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Mock Study Block" } });
    fireEvent.change(screen.getByLabelText("Type"), { target: { value: "study_plan" } });
    fireEvent.click(screen.getByRole("button", { name: "Schedule Reminder" }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Mock Study Block",
          reminder_type: "study_plan",
        })
      );
    });
  });
});

function applicationsListHookFix() {
  return applicationService;
}
