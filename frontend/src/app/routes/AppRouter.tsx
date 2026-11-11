import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../../components/layout/AppShell";
import { ProtectedRoute } from "../../features/authentication/components/ProtectedRoute";
import { LoginPage } from "../../features/authentication/pages/LoginPage";
import { FoundationStatusPage } from "../../features/dashboard/pages/FoundationStatusPage";
import { ProfilePage } from "../../features/profile/pages/ProfilePage";

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
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
