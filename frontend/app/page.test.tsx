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
};

function jsonResponse(status: number, payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

function createMockServer(): MockServer {
  let isLoggedIn = false;
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
      if (payload.username === "user" && payload.password === "password") {
        isLoggedIn = true;
        return jsonResponse(200, { status: "ok" });
      }

      return jsonResponse(401, { detail: "Invalid username or password" });
    }

    if (url === "/api/auth/logout" && method === "POST") {
      isLoggedIn = false;
      return jsonResponse(200, { status: "ok" });
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
});