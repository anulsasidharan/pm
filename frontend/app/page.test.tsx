import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import HomePage from "./page";

type Card = {
  id: string;
  title: string;
};

type Column = {
  id: string;
  name: string;
  cards: Card[];
};

type MockServer = {
  setFailNextPut: () => void;
  getBoard: () => { columns: Column[] };
  seedBoard: (nextBoard: { columns: Column[] }) => void;
  setAiFailureOnce: (message: string) => void;
  setNextAiBoardUpdate: (nextBoard: { columns: Column[] }, reply?: string) => void;
};

function jsonResponse(status: number, payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

function createMockServer(): MockServer {
  let isLoggedIn = false;
  const users = new Map<string, string>([["user", "password"]]);
  let failNextPut = false;
  let board: { columns: Column[] } = {
    columns: [
      {
        id: "todo",
        name: "To Do",
        cards: [
          { id: "c1", title: "Draft project milestones" },
          { id: "c2", title: "Review API contract" }
        ]
      },
      {
        id: "in-progress",
        name: "In Progress",
        cards: [{ id: "c3", title: "Integrate frontend build output" }]
      },
      {
        id: "done",
        name: "Done",
        cards: [{ id: "c4", title: "Scaffold FastAPI in Docker" }]
      }
    ]
  };
  let aiFailureMessage: string | null = null;
  let nextAiBoardUpdate: { board: { columns: Column[] }; reply: string } | null = null;

  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = init?.method ?? "GET";

    if (url === "/api/board" && method === "GET") {
      if (!isLoggedIn) {
        return jsonResponse(401, { detail: "Authentication required" });
      }

      return jsonResponse(200, { board });
    }

    if (url === "/api/board" && method === "PUT") {
      if (!isLoggedIn) {
        return jsonResponse(401, { detail: "Authentication required" });
      }

      if (failNextPut) {
        failNextPut = false;
        return jsonResponse(500, { detail: "save failed" });
      }

      const payload = init?.body ? JSON.parse(String(init.body)) : null;
      board = payload.board;
      return jsonResponse(200, { board });
    }

    if (url === "/api/auth/login" && method === "POST") {
      const payload = init?.body ? JSON.parse(String(init.body)) : {};
      if (users.get(payload.username) === payload.password) {
        isLoggedIn = true;
        return jsonResponse(200, { status: "ok" });
      }

      return jsonResponse(401, { detail: "Invalid username or password" });
    }

    if (url === "/api/auth/register" && method === "POST") {
      const payload = init?.body ? JSON.parse(String(init.body)) : {};
      if (users.has(payload.username)) {
        return jsonResponse(409, { detail: "Username already exists" });
      }

      users.set(payload.username, payload.password);
      isLoggedIn = true;
      return jsonResponse(201, { status: "created" });
    }

    if (url === "/api/auth/logout" && method === "POST") {
      isLoggedIn = false;
      return jsonResponse(200, { status: "ok" });
    }

    if (url === "/api/ai/chat" && method === "POST") {
      if (!isLoggedIn) {
        return jsonResponse(401, { detail: "Authentication required" });
      }

      if (aiFailureMessage) {
        const message = aiFailureMessage;
        aiFailureMessage = null;
        return jsonResponse(502, { detail: message });
      }

      if (nextAiBoardUpdate) {
        board = nextAiBoardUpdate.board;
        const reply = nextAiBoardUpdate.reply;
        nextAiBoardUpdate = null;
        return jsonResponse(200, {
          reply,
          operation_type: "board_update",
          board
        });
      }

      return jsonResponse(200, {
        reply: "Acknowledged",
        operation_type: "chat_only",
        board: null
      });
    }

    return jsonResponse(404, { detail: "not found" });
  }));

  return {
    setFailNextPut() {
      failNextPut = true;
    },
    getBoard() {
      return board;
    },
    seedBoard(nextBoard) {
      board = nextBoard;
    },
    setAiFailureOnce(message) {
      aiFailureMessage = message;
    },
    setNextAiBoardUpdate(nextBoard, reply = "Board updated") {
      nextAiBoardUpdate = { board: nextBoard, reply };
    }
  };
}

async function loginAsDefaultUser() {
  await screen.findByRole("heading", { level: 2, name: "Sign In" });

  fireEvent.change(screen.getByLabelText("Username"), { target: { value: "user" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

  await screen.findByText("Signed in as user");
}

describe("HomePage", () => {
  let server: MockServer;

  beforeEach(() => {
    server = createMockServer();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows login view by default", async () => {
    render(<HomePage />);

    await screen.findByRole("heading", { level: 2, name: "Sign In" });
    expect(screen.queryByRole("heading", { level: 2, name: "To Do" })).not.toBeInTheDocument();
  });

  it("shows an error for invalid credentials", async () => {
    render(<HomePage />);

    await screen.findByRole("heading", { level: 2, name: "Sign In" });

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "wrong" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "creds" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await screen.findByText("Invalid username or password.");
    expect(screen.queryByRole("heading", { level: 2, name: "To Do" })).not.toBeInTheDocument();
  });

  it("allows login and logout", async () => {
    render(<HomePage />);

    await loginAsDefaultUser();

    expect(screen.getByText("Signed in as user")).toBeInTheDocument();
    expect(screen.getByText("To Do")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign Out" }));

    await screen.findByRole("heading", { level: 2, name: "Sign In" });
    expect(screen.queryByText("Signed in as user")).not.toBeInTheDocument();
  });

  it("allows new user registration", async () => {
    render(<HomePage />);

    await screen.findByRole("heading", { level: 2, name: "Sign In" });
    fireEvent.click(screen.getByRole("button", { name: "New here? Create an account" }));

    await screen.findByRole("heading", { level: 2, name: "Sign Up" });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "newuser" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "strongpass123" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Account" }));

    await screen.findByText("Signed in as newuser");
    expect(screen.getByText("To Do")).toBeInTheDocument();
  });

  it("edits a card title and reload keeps latest persisted state", async () => {
    const { unmount } = render(<HomePage />);

    await loginAsDefaultUser();

    fireEvent.click(screen.getAllByRole("button", { name: "Edit" })[0]);
    const input = screen.getByRole("textbox", { name: "Edit Draft project milestones" });
    fireEvent.change(input, { target: { value: "Updated milestone plan" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await screen.findByText("Updated milestone plan");
    expect(screen.queryByText("Draft project milestones")).not.toBeInTheDocument();

    unmount();
    render(<HomePage />);

    await screen.findByText("Signed in as user");
    expect(screen.getByText("Updated milestone plan")).toBeInTheDocument();
  });

  it("adds a new column and persists it", async () => {
    render(<HomePage />);

    await loginAsDefaultUser();

    fireEvent.change(screen.getByPlaceholderText("e.g. Blocked"), { target: { value: "Blocked" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Column" }));

    await screen.findByRole("heading", { level: 2, name: "Blocked" });
    expect(server.getBoard().columns.some((column) => column.name === "Blocked")).toBe(true);
  });

  it("deletes a card from a column and persists update", async () => {
    render(<HomePage />);

    await loginAsDefaultUser();

    fireEvent.click(screen.getByRole("button", { name: "Delete Review API contract" }));

    await waitFor(() => {
      expect(screen.queryByText("Review API contract")).not.toBeInTheDocument();
    });
    expect(server.getBoard().columns.find((column) => column.id === "todo")?.cards).toHaveLength(1);
  });

  it("moves a card from To Do to Done and persists update", async () => {
    render(<HomePage />);

    await loginAsDefaultUser();

    const todoColumn = screen.getByRole("list", { name: "To Do cards" });
    const doneColumn = screen.getByRole("list", { name: "Done cards" });
    const card = within(todoColumn).getByText("Review API contract").closest("li");
    expect(card).not.toBeNull();

    fireEvent.dragStart(card as HTMLElement);
    fireEvent.drop(doneColumn);

    await waitFor(() => {
      expect(within(doneColumn).getByText("Review API contract")).toBeInTheDocument();
    });
    expect(within(todoColumn).queryByText("Review API contract")).not.toBeInTheDocument();
    expect(server.getBoard().columns.find((column) => column.id === "done")?.cards[1]?.title).toBe(
      "Review API contract"
    );
  });

  it("shows save error when board persistence fails", async () => {
    render(<HomePage />);

    await loginAsDefaultUser();
    server.setFailNextPut();

    fireEvent.click(screen.getAllByRole("button", { name: "Edit" })[0]);
    const input = screen.getByRole("textbox", { name: "Edit Draft project milestones" });
    fireEvent.change(input, { target: { value: "Attempted save" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await screen.findByText("Failed to save board changes.");
  });

  it("restores missing fixed columns from persisted board", async () => {
    server.seedBoard({
      columns: [{ id: "todo", name: "To Do", cards: [{ id: "c1", title: "Only one" }] }]
    });

    render(<HomePage />);
    await loginAsDefaultUser();

    expect(screen.getByRole("heading", { level: 2, name: "To Do" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "In Progress" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Done" })).toBeInTheDocument();
    expect(screen.getByText("Only one")).toBeInTheDocument();
  });

  it("renders AI chat messages from user and assistant", async () => {
    render(<HomePage />);
    await loginAsDefaultUser();

    fireEvent.change(screen.getByLabelText("AI message"), {
      target: { value: "Summarize board" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await screen.findByText(/You:/);
    await screen.findByText(/AI:/);
    expect(screen.getByText(/Summarize board/)).toBeInTheDocument();
    expect(screen.getByText(/Acknowledged/)).toBeInTheDocument();
  });

  it("applies AI-triggered board updates to the UI", async () => {
    server.setNextAiBoardUpdate(
      {
        columns: [
          {
            id: "todo",
            name: "To Do",
            cards: [{ id: "c99", title: "AI created task" }]
          },
          { id: "in-progress", name: "In Progress", cards: [] },
          { id: "done", name: "Done", cards: [] }
        ]
      },
      "Added AI card"
    );

    render(<HomePage />);
    await loginAsDefaultUser();

    fireEvent.change(screen.getByLabelText("AI message"), {
      target: { value: "Add a task" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await screen.findByText("Added AI card");
    expect(screen.getByText("AI created task")).toBeInTheDocument();
  });

  it("shows chat error when AI endpoint fails", async () => {
    server.setAiFailureOnce("upstream unavailable");

    render(<HomePage />);
    await loginAsDefaultUser();

    fireEvent.change(screen.getByLabelText("AI message"), {
      target: { value: "Try update" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await screen.findByText("upstream unavailable");
  });
});