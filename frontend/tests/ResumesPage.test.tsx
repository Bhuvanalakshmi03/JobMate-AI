import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ResumesPage } from "../src/features/resume/pages/ResumesPage";
import { resumeService } from "../src/services/resume-service";

function renderResumesPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ResumesPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("ResumesPage", () => {
  it("shows empty state, rejects unsupported files, and uploads a valid PDF", async () => {
    vi.spyOn(resumeService, "listResumes").mockResolvedValue({ items: [], total: 0 });
    const uploadSpy = vi.spyOn(resumeService, "uploadResume").mockResolvedValue({
      id: "res-1",
      original_filename: "student.pdf",
      content_type: "application/pdf",
      file_extension: "pdf",
      file_size_bytes: 1024,
      page_count: 1,
      parse_status: "parsed",
      created_at: "2026-11-11T12:00:00Z",
      updated_at: "2026-11-11T12:00:00Z",
    });

    renderResumesPage();

    await waitFor(() => {
      expect(screen.getByText("No resumes uploaded yet")).toBeInTheDocument();
    });

    const input = screen.getByLabelText("Resume file");
    const badFile = new File(["hello"], "notes.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [badFile] } });

    expect(screen.getByRole("alert")).toHaveTextContent("Only PDF (.pdf) and Word (.docx)");

    const pdfFile = new File(["%PDF-1.4 content"], "student.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [pdfFile] } });
    fireEvent.click(screen.getByRole("button", { name: "Upload Resume" }));

    await waitFor(() => {
      expect(uploadSpy).toHaveBeenCalledWith(pdfFile);
      expect(screen.getByText("Resume uploaded and parsed")).toBeInTheDocument();
    });
  });
});
