import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { JobDetailsPage } from "../src/features/jobs/pages/JobDetailsPage";
import { JobsPage } from "../src/features/jobs/pages/JobsPage";
import { jobService } from "../src/services/job-service";

function renderJobsPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <JobsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function renderJobDetails() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("JobsPage & JobDetailsPage", () => {
  it("discovers jobs, calculates match, and toggles bookmark", async () => {
    const searchSpy = vi.spyOn(jobService, "searchJobs").mockResolvedValue({
      items: [
        {
          id: "job-1",
          source_provider: "openai_web_search",
          title: "Backend Software Engineer",
          company: "Acme Cloud",
          location: "Remote",
          work_mode: "remote",
          experience_level: "entry_level",
          employment_type: "full_time",
          required_skills: ["Python", "FastAPI"],
          preferred_skills: [],
          external_url: "https://careers.acme.io/jobs/1",
          source_domain: "careers.acme.io",
          retrieved_at: "2026-11-11T12:00:00Z",
          is_active: true,
          is_saved: false,
        },
      ],
      total: 1,
      source: "openai_web_search",
      cached: false,
    });
    const saveSpy = vi.spyOn(jobService, "saveJob").mockResolvedValue({
      job_id: "job-1",
      is_saved: true,
      saved_at: "2026-11-11T12:01:00Z",
    });

    renderJobsPage();

    await waitFor(() => {
      expect(screen.getByText("Backend Software Engineer")).toBeInTheDocument();
      expect(screen.getByText("Source: openai_web_search")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Role or keywords"), {
      target: { value: "Backend Engineer" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Discover Jobs" }));

    await waitFor(() => {
      expect(searchSpy).toHaveBeenCalledWith(
        expect.objectContaining({ q: "Backend Engineer" })
      );
    });

    const saveBtn = await screen.findByRole("button", { name: /^Save$/i });
    fireEvent.click(saveBtn);
    await waitFor(() => {
      expect(saveSpy).toHaveBeenCalledWith("job-1");
    });
  });

  it("displays explainable factor breakdown on JobDetailsPage", async () => {
    vi.spyOn(jobService, "getJobDetails").mockResolvedValue({
      id: "job-1",
      source_provider: "openai_web_search",
      title: "Backend Software Engineer",
      company: "Acme Cloud",
      location: "Remote",
      work_mode: "remote",
      experience_level: "entry_level",
      employment_type: "full_time",
      required_skills: ["Python", "FastAPI"],
      preferred_skills: ["Docker"],
      education_requirements: ["B.Tech CS"],
      description: "Build APIs in Python and FastAPI.",
      external_url: "https://careers.acme.io/jobs/1",
      source_domain: "careers.acme.io",
      retrieved_at: "2026-11-11T12:00:00Z",
      is_active: true,
      is_saved: false,
    });
    vi.spyOn(jobService, "calculateMatch").mockResolvedValue({
      id: "m-1",
      user_id: "u-1",
      job_id: "job-1",
      algorithm_version: "v1.0.0",
      overall_score: 86.5,
      factor_scores: {
        technical_skill_compatibility: 1.0,
        job_role_similarity: 0.85,
      },
      weights_used: {
        technical_skill_compatibility: 0.35,
        job_role_similarity: 0.2,
      },
      matching_skills: ["Python", "FastAPI"],
      missing_skills: ["Docker"],
      match_explanation: "Overall match score 86.5% (v1.0.0): strong skill fit.",
      recommended_preparation: ["Build hands-on familiarity with Docker"],
      computed_at: "2026-11-11T12:02:00Z",
    });

    renderJobDetails();

    await waitFor(() => {
      expect(screen.getByText("Backend Software Engineer")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /calculate match/i }));

    await waitFor(() => {
      expect(screen.getByText("Explainable Job Match Breakdown")).toBeInTheDocument();
      expect(screen.getByText("87% Match")).toBeInTheDocument();
      expect(screen.getByText("Build hands-on familiarity with Docker")).toBeInTheDocument();
    });
  });
});
