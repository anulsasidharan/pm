import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { ApiError, fetchBoard, login, logout, saveBoard } from "./api";

function jsonResponse(status: number, payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends login request with credentials", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(jsonResponse(200, { status: "ok" }));

    await login({ username: "user", password: "password" });

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        credentials: "include"
      })
    );
  });

  it("fetches and unwraps board payload", async () => {
    const board = { columns: [{ id: "todo", name: "To Do", cards: [] }] };
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(jsonResponse(200, { board }));

    await expect(fetchBoard()).resolves.toEqual(board);
  });

  it("surfaces API detail message on failures", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(jsonResponse(401, { detail: "Authentication required" }));

    await expect(fetchBoard()).rejects.toEqual(new ApiError(401, "Authentication required"));
  });

  it("saves board and calls logout endpoint", async () => {
    const board = { columns: [{ id: "done", name: "Done", cards: [] }] };
    const mockFetch = vi.mocked(fetch);
    mockFetch
      .mockResolvedValueOnce(jsonResponse(200, { board }))
      .mockResolvedValueOnce(jsonResponse(200, { status: "ok" }));

    await expect(saveBoard(board)).resolves.toEqual(board);
    await expect(logout()).resolves.toBeUndefined();

    expect(mockFetch).toHaveBeenNthCalledWith(
      1,
      "/api/board",
      expect.objectContaining({ method: "PUT" })
    );
    expect(mockFetch).toHaveBeenNthCalledWith(
      2,
      "/api/auth/logout",
      expect.objectContaining({ method: "POST" })
    );
  });
});
