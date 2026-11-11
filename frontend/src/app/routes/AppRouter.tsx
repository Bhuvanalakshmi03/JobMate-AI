import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../../components/layout/AppShell";
import { AgentCopilotPage } from "../../features/agents/pages/AgentCopilotPage";
import { ApplicationDetailsPage } from "../../features/applications/pages/ApplicationDetailsPage";
import { ApplicationsPage } from "../../features/applications/pages/ApplicationsPage";
import { ApprovalsPage } from "../../features/approvals/pages/ApprovalsPage";
import { ProtectedRoute } from "../../features/authentication/components/ProtectedRoute";
import { LoginPage } from "../../features/authentication/pages/LoginPage";
import { WeeklyCalendarPage } from "../../features/calendar/pages/WeeklyCalendarPage";
import { FoundationStatusPage } from "../../features/dashboard/pages/FoundationStatusPage";
import { DocumentEditorPage } from "../../features/documents/pages/DocumentEditorPage";
import { DocumentsPage } from "../../features/documents/pages/DocumentsPage";
import { InterviewSessionPage } from "../../features/interviews/pages/InterviewSessionPage";
import { InterviewsPage } from "../../features/interviews/pages/InterviewsPage";
import { JobDetailsPage } from "../../features/jobs/pages/JobDetailsPage";
import { JobsPage } from "../../features/jobs/pages/JobsPage";
import { ProfilePage } from "../../features/profile/pages/ProfilePage";
import { ResumeAnalysisPage } from "../../features/resume/pages/ResumeAnalysisPage";
import { ResumesPage } from "../../features/resume/pages/ResumesPage";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell>
              <FoundationStatusPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <AppShell>
              <ProfilePage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/resumes"
        element={
          <ProtectedRoute>
            <AppShell>
              <ResumesPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/resumes/:resumeId"
        element={
          <ProtectedRoute>
            <AppShell>
              <ResumeAnalysisPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/jobs"
        element={
          <ProtectedRoute>
            <AppShell>
              <JobsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/jobs/:jobId"
        element={
          <ProtectedRoute>
            <AppShell>
              <JobDetailsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/documents"
        element={
          <ProtectedRoute>
            <AppShell>
              <DocumentsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/documents/:documentId"
        element={
          <ProtectedRoute>
            <AppShell>
              <DocumentEditorPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/applications"
        element={
          <ProtectedRoute>
            <AppShell>
              <ApplicationsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/applications/:applicationId"
        element={
          <ProtectedRoute>
            <AppShell>
              <ApplicationDetailsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/copilot"
        element={
          <ProtectedRoute>
            <AppShell>
              <AgentCopilotPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/calendar"
        element={
          <ProtectedRoute>
            <AppShell>
              <WeeklyCalendarPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/approvals"
        element={
          <ProtectedRoute>
            <AppShell>
              <ApprovalsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/interviews"
        element={
          <ProtectedRoute>
            <AppShell>
              <InterviewsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/interviews/:sessionId"
        element={
          <ProtectedRoute>
            <AppShell>
              <InterviewSessionPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
