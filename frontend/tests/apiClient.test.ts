import { describe, expect, it, vi } from "vitest";

import { ApiClientError, apiRequest } from "../src/services/api-client";

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
});

