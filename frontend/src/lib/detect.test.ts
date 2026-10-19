import { describe, expect, it } from "vitest";
import { tileFromInput } from "./detect";

describe("tileFromInput", () => {
  it("detects email", () => {
    expect(tileFromInput("a@b.co").type).toBe("social");
  });
  it("detects repo", () => {
    expect(tileFromInput("org/repo").type).toBe("repo");
  });
  it("detects video", () => {
    expect(tileFromInput("https://www.youtube.com/watch?v=abc").type).toBe("video");
  });
});
