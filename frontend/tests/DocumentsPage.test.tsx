import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { DocumentEditorPage } from "../src/features/documents/pages/DocumentEditorPage";
import { DocumentsPage } from "../src/features/documents/pages/DocumentsPage";
import { documentService } from "../src/services/document-service";
import { jobService } from "../src/services/job-service";
import { resumeService } from "../src/services/resume-service";

function renderDocumentsPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/documents"]}>
        <Routes>
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/documents/:documentId" element={<DocumentEditorPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("DocumentsPage & DocumentEditorPage", () => {
  it("generates a tailored resume, displays editor & version history, and saves edits", async () => {
    vi.spyOn(jobService, "searchJobs").mockResolvedValue({
      items: [
        {
          id: "job-1",
          source_provider: "openai_web_search",
          title: "Backend Engineer",
          company: "Orbit Systems",
          work_mode: "remote",
          experience_level: "entry_level",
          employment_type: "full_time",
          required_skills: ["Python"],
          preferred_skills: [],
          external_url: "https://careers.orbitsystems.io/backend",
          retrieved_at: "2026-11-11T12:00:00Z",
          is_active: true,
          is_saved: false,
        },
      ],
      total: 1,
      source: "database",
      cached: false,
    });
    vi.spyOn(resumeService, "listResumes").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(documentService, "listDocuments").mockResolvedValue({ items: [], total: 0 });

    const createdDoc = {
      id: "doc-1",
      user_id: "u-1",
      job_id: "job-1",
      document_type: "tailored_resume",
      title: "Backend Engineer at Orbit Systems — Tailored Resume",
      version_group_id: "vg-1",
      version: 1,
      content_markdown: "# Maya Rao\n\nBackend developer.",
      factuality_report: {
        is_grounded: true,
        verified_fact_ids: ["f-1"],
        checked_claims_count: 3,
        unsupported_claims: [],
      },
      is_user_edited: false,
      created_at: "2026-11-11T12:00:00Z",
      updated_at: "2026-11-11T12:00:00Z",
    };

    const tailorSpy = vi.spyOn(documentService, "tailorResume").mockResolvedValue(createdDoc);
    vi.spyOn(documentService, "getDocument").mockResolvedValue({
      ...createdDoc,
      versions: [{ id: "doc-1", version: 1, is_user_edited: false, created_at: "2026-11-11T12:00:00Z" }],
    });
    const updateSpy = vi.spyOn(documentService, "updateDocument").mockResolvedValue({
      ...createdDoc,
      id: "doc-2",
      version: 2,
      is_user_edited: true,
      content_markdown: "# Maya Rao\n\nEdited summary.",
      versions: [
        { id: "doc-2", version: 2, is_user_edited: true, created_at: "2026-11-11T12:05:00Z" },
        { id: "doc-1", version: 1, is_user_edited: false, created_at: "2026-11-11T12:00:00Z" },
      ],
    });

    renderDocumentsPage();

    await waitFor(() => {
      expect(screen.getByText("No generated documents yet")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Backend Engineer — Orbit Systems")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Generate Document" }));

    await waitFor(() => {
      expect(tailorSpy).toHaveBeenCalledWith({
        job_id: "job-1",
        resume_id: null,
        focus_instructions: null,
      });
      expect(screen.getByText("Editable Content")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Content (Markdown / ATS plain layout)"), {
      target: { value: "# Maya Rao\n\nEdited summary." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        "doc-1",
        expect.objectContaining({
          content_markdown: "# Maya Rao\n\nEdited summary.",
          create_new_version: true,
        })
      );
    });
  });
});
