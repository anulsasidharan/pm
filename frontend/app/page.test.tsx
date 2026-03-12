import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "./page";

function loginAsDefaultUser() {
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: "user" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
}

describe("HomePage", () => {
  it("shows login view by default", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { level: 2, name: "Sign In" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: "To Do" })).not.toBeInTheDocument();
  });

  it("shows an error for invalid credentials", () => {
    render(<HomePage />);

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "wrong" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "creds" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(screen.getByText("Invalid username or password.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: "To Do" })).not.toBeInTheDocument();
  });

  it("allows login and logout", () => {
    render(<HomePage />);

    loginAsDefaultUser();

    expect(screen.getByText("Signed in as user")).toBeInTheDocument();
    expect(screen.getByText("To Do")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign Out" }));

    expect(screen.getByRole("heading", { level: 2, name: "Sign In" })).toBeInTheDocument();
    expect(screen.queryByText("Signed in as user")).not.toBeInTheDocument();
  });

  it("edits a card title after login", () => {
    render(<HomePage />);

    loginAsDefaultUser();

    fireEvent.click(screen.getAllByRole("button", { name: "Edit" })[0]);
    const input = screen.getByRole("textbox", { name: "Edit Draft project milestones" });
    fireEvent.change(input, { target: { value: "Updated milestone plan" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(screen.getByText("Updated milestone plan")).toBeInTheDocument();
    expect(screen.queryByText("Draft project milestones")).not.toBeInTheDocument();
  });

  it("moves a card from To Do to Done after login", () => {
    render(<HomePage />);

    loginAsDefaultUser();

    const todoColumn = screen.getByRole("list", { name: "To Do cards" });
    const doneColumn = screen.getByRole("list", { name: "Done cards" });
    const card = within(todoColumn).getByText("Review API contract").closest("li");
    expect(card).not.toBeNull();

    fireEvent.dragStart(card as HTMLElement);
    fireEvent.drop(doneColumn);

    expect(within(doneColumn).getByText("Review API contract")).toBeInTheDocument();
    expect(within(todoColumn).queryByText("Review API contract")).not.toBeInTheDocument();
  });

  it("ignores column drop when no card is being dragged", () => {
    render(<HomePage />);

    loginAsDefaultUser();

    const doneColumn = screen.getByRole("list", { name: "Done cards" });
    fireEvent.drop(doneColumn);

    expect(within(doneColumn).queryByText("Review API contract")).not.toBeInTheDocument();
  });

  it("supports dropping onto a specific card target", () => {
    render(<HomePage />);

    loginAsDefaultUser();

    const todoColumn = screen.getByRole("list", { name: "To Do cards" });
    const doneColumn = screen.getByRole("list", { name: "Done cards" });
    const dragged = within(todoColumn).getByText("Review API contract").closest("li");
    const doneCardTarget = within(doneColumn).getByText("Scaffold FastAPI in Docker").closest("li");
    expect(dragged).not.toBeNull();
    expect(doneCardTarget).not.toBeNull();

    fireEvent.dragStart(dragged as HTMLElement);
    fireEvent.drop(doneCardTarget as HTMLElement);

    const doneCards = within(doneColumn).getAllByRole("listitem");
    expect(doneCards[0]).toHaveTextContent("Review API contract");
  });
});