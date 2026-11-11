import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../../components/layout/AppShell";
import { ProtectedRoute } from "../../features/authentication/components/ProtectedRoute";
import { LoginPage } from "../../features/authentication/pages/LoginPage";
import { FoundationStatusPage } from "../../features/dashboard/pages/FoundationStatusPage";
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
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
