import { describe, expect, it, vi } from "vitest";

import { ApiClientError, apiRequest, getApiBaseUrl } from "../src/services/api-client";

describe("apiRequest", () => {
  it("parses JSON response on 200 OK", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      })
    );

    const data = await apiRequest<{ status: string }>("/health");
    expect(data).toEqual({ status: "ok" });
    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/v1/health",
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("throws structured ApiClientError on backend error envelope", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "NOT_FOUND",
            message: "Item missing",
            request_id: "req-99",
            timestamp: "2026-11-10T12:00:00Z",
          },
        }),
        {
          status: 404,
          headers: { "content-type": "application/json" },
        }
      )
    );

    await expect(apiRequest("/missing")).rejects.toMatchObject({
      name: "ApiClientError",
      status: 404,
      code: "NOT_FOUND",
      message: "Item missing",
      requestId: "req-99",
    } satisfies Partial<ApiClientError>);
  });

  it("retries transient GET network failures once and reports JobMate AI message on persistent error", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      );

    const recovered = await apiRequest<{ ok: boolean }>("/health");
    expect(recovered).toEqual({ ok: true });
    expect(fetchSpy).toHaveBeenCalledTimes(2);

    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(
      apiRequest("/copilot/conversations", { method: "POST", body: "{}" })
    ).rejects.toMatchObject({
      code: "NETWORK_ERROR",
      message: expect.stringContaining("JobMate AI API server"),
    });
  });

  it("maps jobmate.techcreed.in frontend host to jobmateapi.techcreed.in API base URL", () => {
    const originalLocation = window.location;
    Object.defineProperty(window, "location", {
      value: { hostname: "jobmate.techcreed.in", protocol: "https:" },
      configurable: true,
    });
    try {
      expect(getApiBaseUrl()).toBe("https://jobmateapi.techcreed.in/api/v1");
    } finally {
      Object.defineProperty(window, "location", {
        value: originalLocation,
        configurable: true,
      });
    }
  });
});

