import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button } from "./button";

describe("Button", () => {
  it("retains native disabled behaviour", () => {
    render(<Button disabled>Upload dataset</Button>);
    expect(screen.getByRole("button", { name: "Upload dataset" })).toBeDisabled();
  });
});
