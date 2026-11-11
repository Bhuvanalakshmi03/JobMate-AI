import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApplicationDetailsPage } from "../src/features/applications/pages/ApplicationDetailsPage";
import { ApplicationsPage } from "../src/features/applications/pages/ApplicationsPage";
import { applicationService } from "../src/services/application-service";
import { documentService } from "../src/services/document-service";
import { jobService } from "../src/services/job-service";
import type { ApplicationDetail, ApplicationItem } from "../src/types/application";

function renderApplicationsRoutes(initialPath = "/applications") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/applications/:applicationId" element={<ApplicationDetailsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const BASE_ITEM: ApplicationItem = {
  id: "app-1",
  user_id: "u-1",
  job_id: "job-1",
  tailored_resume_id: null,
  cover_letter_id: null,
  company_name: "Orbit Systems",
  role_title: "Platform Engineer",
  job_url: "https://careers.orbitsystems.io/platform",
  location: "Remote",
  status: "SAVED",
  allowed_next_statuses: ["PREPARING", "WITHDRAWN"],
  applied_at: null,
  deadline_at: "2026-11-20T18:00:00Z",
  follow_up_at: null,
  notes: "Referral submitted by alumni mentor.",
  created_at: "2026-11-11T10:00:00Z",
  updated_at: "2026-11-11T10:00:00Z",
};

const BASE_DETAIL: ApplicationDetail = {
  ...BASE_ITEM,
  history: [
    {
      id: "hist-1",
      from_status: null,
      to_status: "SAVED",
      note: "Application saved to tracker",
      changed_at: "2026-11-11T10:00:00Z",
    },
  ],
};

describe("ApplicationsPage & ApplicationDetailsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates an application, filters by status, and transitions status cleanly", async () => {
    vi.spyOn(jobService, "searchJobs").mockResolvedValue({
      items: [],
      total: 0,
      source: "database",
      cached: false,
    });
    const listSpy = vi.spyOn(applicationService, "listApplications").mockResolvedValue({
      items: [BASE_ITEM],
      total: 1,
    });
    vi.spyOn(applicationService, "getSummary").mockResolvedValue({
      total_applications: 1,
      counts_by_status: { SAVED: 1 },
      upcoming_deadlines: [BASE_ITEM],
    });
    const createSpy = vi
      .spyOn(applicationService, "createApplication")
      .mockResolvedValue(BASE_DETAIL);
    const transitionSpy = vi
      .spyOn(applicationService, "transitionApplication")
      .mockResolvedValue({
        ...BASE_DETAIL,
        status: "PREPARING",
        allowed_next_statuses: ["AWAITING_APPROVAL", "SAVED", "WITHDRAWN"],
      });

    renderApplicationsRoutes();

    await waitFor(() => {
      expect(screen.getAllByText("Platform Engineer").length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getByRole("button", { name: "New Application" }));
    fireEvent.change(screen.getByLabelText("Company Name"), {
      target: { value: "Northstar Labs" },
    });
    fireEvent.change(screen.getByLabelText("Role Title"), {
      target: { value: "Backend Intern" },
    });
    fireEvent.change(screen.getByLabelText("Personal Notes (optional)"), {
      target: { value: "Apply after updating resume." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Application" }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          company_name: "Northstar Labs",
          role_title: "Backend Intern",
          notes: "Apply after updating resume.",
        })
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Move to Preparing" }));
    await waitFor(() => {
      expect(transitionSpy).toHaveBeenCalledWith("app-1", {
        target_status: "PREPARING",
        note: undefined,
      });
    });

    fireEvent.click(screen.getByRole("button", { name: /^Preparing/ }));
    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledWith({
        status: "PREPARING",
        limit: 50,
        offset: 0,
      });
    });
  });

  it("renders details page, activity history, notes update, and controlled status transition", async () => {
    vi.spyOn(documentService, "listDocuments").mockResolvedValue({
      items: [],
      total: 0,
    });
    const preparingDetail: ApplicationDetail = {
      ...BASE_DETAIL,
      status: "AWAITING_APPROVAL",
      allowed_next_statuses: ["SUBMITTED", "PREPARING", "WITHDRAWN"],
      history: [
        ...BASE_DETAIL.history,
        {
          id: "hist-2",
          from_status: "PREPARING",
          to_status: "AWAITING_APPROVAL",
          note: "Ready for submission review",
          changed_at: "2026-11-11T11:30:00Z",
        },
      ],
    };
    vi.spyOn(applicationService, "getApplication").mockResolvedValue(preparingDetail);
    const updateSpy = vi
      .spyOn(applicationService, "updateApplication")
      .mockResolvedValue({ ...preparingDetail, notes: "Updated follow-up notes" });
    const transitionSpy = vi
      .spyOn(applicationService, "transitionApplication")
      .mockResolvedValue({
        ...preparingDetail,
        status: "SUBMITTED",
        allowed_next_statuses: ["INTERVIEW_SCHEDULED", "REJECTED", "OFFER_RECEIVED", "WITHDRAWN"],
        history: [
          ...preparingDetail.history,
          {
            id: "hist-3",
            from_status: "AWAITING_APPROVAL",
            to_status: "SUBMITTED",
            note: "Submitted portal confirmation #441",
            changed_at: "2026-11-11T12:00:00Z",
          },
        ],
      });

    renderApplicationsRoutes("/applications/app-1");

    await waitFor(() => {
      expect(screen.getByText("Platform Engineer — Orbit Systems")).toBeInTheDocument();
      expect(screen.getByText("Ready for submission review")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Notes"), {
      target: { value: "Updated follow-up notes" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        "app-1",
        expect.objectContaining({ notes: "Updated follow-up notes" })
      );
      expect(screen.getByText("Changes saved")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Transition Note (optional)"), {
      target: { value: "Submitted portal confirmation #441" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Move to Submitted" }));

    await waitFor(() => {
      expect(transitionSpy).toHaveBeenCalledWith("app-1", {
        target_status: "SUBMITTED",
        note: "Submitted portal confirmation #441",
      });
    });
  });

  it("renders error alert when loading applications fails", async () => {
    vi.spyOn(applicationService, "listApplications").mockRejectedValue(
      new Error("Applications service unavailable")
    );
    vi.spyOn(applicationService, "getSummary").mockRejectedValue(
      new Error("Applications service unavailable")
    );

    renderApplicationsRoutes();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Applications service unavailable");
    });
  });
});
