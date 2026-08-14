import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { AppErrorBoundary } from "./AppErrorBoundary";

function BrokenView(): never {
  throw new Error("render failed");
}

afterEach(() => {
  vi.restoreAllMocks();
});

test("shows a recovery screen instead of a blank page after a render failure", () => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  render(
    <AppErrorBoundary>
      <BrokenView />
    </AppErrorBoundary>,
  );
  expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível carregar o Atlas");
  expect(screen.getByRole("button", { name: "Recarregar página" })).toBeInTheDocument();
});
