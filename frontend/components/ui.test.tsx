import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button, StatusBadge } from "./ui";

describe("StatusBadge", () => {
  it("renders a readable label for a processing document", () => {
    render(<StatusBadge status="processing" />);
    expect(screen.getByText("Processing")).toBeInTheDocument();
  });

  it("falls back to the raw status", () => {
    render(<StatusBadge status="custom_state" />);
    expect(screen.getByText("custom_state")).toBeInTheDocument();
  });
});

describe("Button", () => {
  it("defaults to a non-submitting button", () => {
    render(<Button>Upload</Button>);
    expect(screen.getByRole("button", { name: "Upload" })).toHaveAttribute("type", "button");
  });
});
