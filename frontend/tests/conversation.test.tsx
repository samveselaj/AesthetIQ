import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Badge, EmptyState } from "@/components/ui";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

describe("UI primitives", () => {
  it("renders a Badge with its children", () => {
    render(wrap(<Badge tone="danger">Escalated</Badge>));
    expect(screen.getByText("Escalated")).toBeInTheDocument();
  });

  it("renders an empty state title and description", () => {
    render(
      wrap(
        <EmptyState title="No conversations yet" description="Waiting for the first message." />
      )
    );
    expect(screen.getByText("No conversations yet")).toBeInTheDocument();
    expect(screen.getByText("Waiting for the first message.")).toBeInTheDocument();
  });
});
