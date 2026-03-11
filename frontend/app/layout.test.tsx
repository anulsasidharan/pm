import React from "react";
import { describe, expect, it } from "vitest";
import RootLayout, { metadata } from "./layout";

describe("RootLayout", () => {
  it("exposes expected page metadata", () => {
    expect(metadata.title).toBe("Project Management MVP");
    expect(metadata.description).toContain("Kanban board frontend");
  });

  it("returns an html element with lang=en and body wrapper", () => {
    const tree = RootLayout({ children: <div>Child</div> });

    expect(tree.type).toBe("html");
    expect(tree.props.lang).toBe("en");
    expect(tree.props.children.type).toBe("body");
    expect(tree.props.children.props.children.props.children).toBe("Child");
  });
});
