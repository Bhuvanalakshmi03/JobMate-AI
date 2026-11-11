import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ResumeAnalysisPage } from "../src/features/resume/pages/ResumeAnalysisPage";
import { resumeService } from "../src/services/resume-service";

function renderAnalysisPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/resumes/res-1"]}>
        <Routes>
          <Route path="/resumes/:resumeId" element={<ResumeAnalysisPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("ResumeAnalysisPage", () => {
  it("renders analysis summary and verifies extracted resume facts", async () => {
    vi.spyOn(resumeService, "getAnalysis").mockResolvedValue({
      resume: {
        id: "res-1",
        original_filename: "maya_resume.pdf",
        content_type: "application/pdf",
        file_extension: "pdf",
        file_size_bytes: 2048,
        page_count: 1,
        parse_status: "analyzed",
        completeness_score: 88,
        created_at: "2026-11-11T12:00:00Z",
        updated_at: "2026-11-11T12:00:00Z",
      },
      completeness_score: 88,
      analysis_summary: {
        overall_assessment: "Solid backend engineering resume.",
        strengths: ["Strong FastAPI project"],
        missing_skills: ["Docker"],
        recommendations: ["Quantify API latency gains"],
      },
      facts: [
        {
          id: "fact-1",
          resume_id: "res-1",
          fact_type: "skill",
          title: "Python",
          source_section: "Skills",
          evidence_excerpt: "Languages: Python, TypeScript",
          confidence: 0.96,
          verification_status: "pending",
          is_verified: false,
          structured_data: { evidence_matched: true, category: "language" },
          created_at: "2026-11-11T12:00:00Z",
          updated_at: "2026-11-11T12:00:00Z",
        },
      ],
    });

    const patchSpy = vi.spyOn(resumeService, "patchFacts").mockResolvedValue({
      facts: [],
      verified_count: 1,
      synced_to_profile: true,
      synced_skills_count: 1,
    });

    renderAnalysisPage();

    await waitFor(() => {
      expect(screen.getByText("maya_resume.pdf")).toBeInTheDocument();
      expect(screen.getByText("Python")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^Verify$/i }));

    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalledWith(
        "res-1",
        [{ fact_id: "fact-1", action: "verify" }],
        true
      );
      expect(screen.getByText("Verification saved")).toBeInTheDocument();
    });
  });
});
