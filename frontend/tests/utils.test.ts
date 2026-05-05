import { describe, expect, it } from "vitest";
import { cn, formatRelative } from "@/lib/utils";

describe("cn", () => {
  it("joins classes", () => {
    expect(cn("a", "b")).toBe("a b");
  });
  it("merges conflicting tailwind classes with later winning", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
  it("handles falsy values", () => {
    expect(cn("a", false, null, undefined, "b")).toBe("a b");
  });
});

describe("formatRelative", () => {
  it("returns empty string for null", () => {
    expect(formatRelative(null)).toBe("");
  });
  it("reports just now for recent dates", () => {
    expect(formatRelative(new Date())).toBe("just now");
  });
});
