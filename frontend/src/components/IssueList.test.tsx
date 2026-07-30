import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { IssueList } from "./IssueList";

describe("IssueList", () => {
  it("renders issue title, source, risk level, and status", () => {
    render(
      <IssueList
        filters={{}}
        issues={[
          {
            id: 1,
            title: "法审晚于签订日期",
            issueType: "process_audit",
            source: "ai",
            riskLevel: "high",
            status: "pending",
          },
        ]}
        onBatchDelete={() => {}}
        onBatchUpdate={() => {}}
        onFilterChange={() => {}}
        selectedIssueId={1}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("法审晚于签订日期")).toBeTruthy();
    expect(screen.getByText("high")).toBeTruthy();
    expect(screen.getByText("ai")).toBeTruthy();
    expect(screen.getByText("pending")).toBeTruthy();
  });
});
