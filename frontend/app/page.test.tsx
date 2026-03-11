import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "./page";

describe("HomePage", () => {
  it("renders the kanban board columns", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Project Management MVP");
    expect(screen.getByText("To Do")).toBeInTheDocument();
    expect(screen.getByText("In Progress")).toBeInTheDocument();
    expect(screen.getByText("Done")).toBeInTheDocument();
  });

  it("edits a card title", () => {
    render(<HomePage />);

    fireEvent.click(screen.getAllByRole("button", { name: "Edit" })[0]);
    const input = screen.getByRole("textbox", { name: "Edit Draft project milestones" });
    fireEvent.change(input, { target: { value: "Updated milestone plan" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(screen.getByText("Updated milestone plan")).toBeInTheDocument();
    expect(screen.queryByText("Draft project milestones")).not.toBeInTheDocument();
  });

  it("moves a card from To Do to Done", () => {
    render(<HomePage />);

    const todoColumn = screen.getByRole("list", { name: "To Do cards" });
    const doneColumn = screen.getByRole("list", { name: "Done cards" });
    const card = within(todoColumn).getByText("Review API contract").closest("li");
    expect(card).not.toBeNull();

    fireEvent.dragStart(card as HTMLElement);
    fireEvent.drop(doneColumn);

    expect(within(doneColumn).getByText("Review API contract")).toBeInTheDocument();
    expect(within(todoColumn).queryByText("Review API contract")).not.toBeInTheDocument();
  });
});