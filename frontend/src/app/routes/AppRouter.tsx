import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../../components/layout/AppShell";
import { ApplicationDetailsPage } from "../../features/applications/pages/ApplicationDetailsPage";
import { ApplicationsPage } from "../../features/applications/pages/ApplicationsPage";
import { ProtectedRoute } from "../../features/authentication/components/ProtectedRoute";
import { LoginPage } from "../../features/authentication/pages/LoginPage";
import { FoundationStatusPage } from "../../features/dashboard/pages/FoundationStatusPage";
import { DocumentEditorPage } from "../../features/documents/pages/DocumentEditorPage";
import { DocumentsPage } from "../../features/documents/pages/DocumentsPage";
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
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
