import { describe, expect, it } from "vitest";
import capability from "../../src-tauri/capabilities/default.json";

describe("main window capabilities", () => {
  it("allows the message IPC used by deletion confirmation dialogs", () => {
    expect(capability.windows).toContain("main");
    expect(capability.permissions).toContain("dialog:allow-message");
  });
});
