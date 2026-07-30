import { describe, expect, it } from "vitest";
import { loadWorkspaceState, saveWorkspaceState } from "./workspace";

describe("workspace state", () => {
  it("persists selected case and filters", () => {
    saveWorkspaceState({
      selectedCaseId: 3,
      selectedIssueId: 9,
      filters: { riskLevel: "high" },
    });
    expect(loadWorkspaceState()).toEqual({
      selectedCaseId: 3,
      selectedIssueId: 9,
      filters: { riskLevel: "high" },
    });
  });
});
