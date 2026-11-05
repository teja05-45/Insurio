import { describe, expect, it } from "vitest";

import { formatBytes, formatPages, initials, statusTone } from "./format";

describe("formatBytes", () => {
  it("formats byte sizes with units", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1024)).toBe("1.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});

describe("formatPages", () => {
  it("collapses a single page and expands ranges", () => {
    expect(formatPages(4, 4)).toBe("page 4");
    expect(formatPages(4, 6)).toBe("pages 4–6");
  });
});

describe("statusTone", () => {
  it("maps statuses to semantic tones", () => {
    expect(statusTone("ready")).toBe("success");
    expect(statusTone("processing")).toBe("warning");
    expect(statusTone("failed")).toBe("danger");
    expect(statusTone("queued")).toBe("neutral");
  });
});

describe("initials", () => {
  it("uses the name when present and the email otherwise", () => {
    expect(initials("Asha Rao", "asha@example.com")).toBe("AR");
    expect(initials("", "asha@example.com")).toBe("AE");
  });
});
