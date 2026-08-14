import { describe, expect, it, vi } from "vitest";
import { createDemoResponse, getDemoSourceUrl, isDemoMode } from "./demo";

describe("demo mode", () => {
  it("is enabled only by the explicit query parameter", () => {
    window.history.replaceState({}, "", "/?demo=1");
    expect(isDemoMode()).toBe(true);
    window.history.replaceState({}, "", "/");
    expect(isDemoMode()).toBe(false);
  });

  it("returns local grounded evidence without a backend", async () => {
    vi.useFakeTimers();
    const responsePromise = createDemoResponse("Quais decisões foram registradas?");
    await vi.advanceTimersByTimeAsync(450);
    const response = await responsePromise;
    vi.useRealTimers();

    expect(response.sufficient_evidence).toBe(true);
    expect(response.citations).toHaveLength(2);
    expect(response.answer).toContain("Rota 120");
    expect(getDemoSourceUrl(response.citations[0].document_id)).toContain("github.com");
  });
});
