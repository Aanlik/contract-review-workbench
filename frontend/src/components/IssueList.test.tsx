import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { IssueList } from "./IssueList";

describe("IssueList", () => {
  it("renders Chinese labels for source, risk level, and status", () => {
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
    expect(document.querySelector(".risk-tag")?.textContent).toBe("高风险");
    expect(document.querySelector(".source-tag")?.textContent).toBe("人工智能审查");
    expect(document.querySelector(".status-tag")?.textContent).toBe("待处理");
    expect(screen.queryByText("high")).toBeNull();
    expect(screen.queryByText("ai")).toBeNull();
    expect(screen.queryByText("pending")).toBeNull();
  });
});
