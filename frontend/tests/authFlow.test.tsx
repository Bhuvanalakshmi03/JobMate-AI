import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppRouter } from "../src/app/routes/AppRouter";
import { AuthProvider } from "../src/features/authentication/hooks/useAuth";
import { ApiClientError } from "../src/services/api-client";
import { authService } from "../src/services/auth-service";

function renderRouterAt(initialPath: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <AuthProvider>
          <AppRouter />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Authentication flow", () => {
  it("redirects unauthenticated users to /login and renders Google OAuth button", async () => {
    vi.spyOn(authService, "getMe").mockRejectedValue(
      new ApiClientError({ status: 401, code: "AUTHENTICATION_FAILED", message: "Unauthorized" })
    );
    vi.spyOn(authService, "getConfig").mockResolvedValue({
      google_oauth_enabled: true,
      dev_auth_enabled: false,
    });

    renderRouterAt("/profile");

    await waitFor(() => {
      expect(screen.getByText("Sign in to CareerPilot AI")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /continue with google/i })).toBeInTheDocument();
    });
    expect(screen.queryByText(/local development sign-in/i)).not.toBeInTheDocument();
  });

  it("supports dev sign-in when backend enables dev_auth_enabled", async () => {
    vi.spyOn(authService, "getMe").mockRejectedValue(
      new ApiClientError({ status: 401, code: "AUTHENTICATION_FAILED", message: "Unauthorized" })
    );
    vi.spyOn(authService, "getConfig").mockResolvedValue({
      google_oauth_enabled: false,
      dev_auth_enabled: true,
    });
    const devLoginSpy = vi.spyOn(authService, "devLogin").mockResolvedValue({
      access_token: "tok-1",
      token_type: "bearer",
      expires_at: "2026-11-18T12:00:00Z",
      is_demo_auth: true,
      user: {
        id: "u-1",
        email: "student@careerpilot.local",
        full_name: "Demo Student",
        oauth_provider: "dev",
        timezone: "UTC",
        created_at: "2026-11-11T12:00:00Z",
        is_demo_auth: true,
      },
    });

    renderRouterAt("/login");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /sign in \(dev mode\)/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /sign in \(dev mode\)/i }));

    await waitFor(() => {
      expect(devLoginSpy).toHaveBeenCalledTimes(1);
    });
  });
});

