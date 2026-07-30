import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CasesPage } from "../pages/CasesPage";

const mockCases = [
  {
    id: 1,
    title: "测试合同A",
    note: "备注A",
    status: "completed",
    currentVersion: 2,
    highestRiskLevel: "high",
    issueCount: 5,
    createdAt: "2026-07-30T10:00:00Z",
    updatedAt: "2026-07-30T12:00:00Z",
  },
  {
    id: 2,
    title: "测试合同B",
    note: null,
    status: "created",
    currentVersion: 1,
    highestRiskLevel: null,
    issueCount: 0,
    createdAt: "2026-07-31T08:00:00Z",
    updatedAt: "2026-07-31T08:00:00Z",
  },
];

afterEach(cleanup);

function renderCases(props?: Partial<React.ComponentProps<typeof CasesPage>>) {
  const defaults = {
    cases: mockCases,
    onDelete: () => {},
    onExport: () => {},
    onOpen: () => {},
    onRename: () => {},
    onSearch: () => {},
  };
  return render(<CasesPage {...defaults} {...props} />);
}

describe("CasesPage", () => {
  it("renders case list with titles", () => {
    renderCases();
    expect(screen.getByText("测试合同A")).toBeTruthy();
    expect(screen.getByText("测试合同B")).toBeTruthy();
    expect(screen.getByText("2 条记录")).toBeTruthy();
  });

  it("shows risk level in case rows", () => {
    const { container } = renderCases();
    const riskElements = container.querySelectorAll(".case-risk");
    expect(riskElements.length).toBe(2);
    expect(riskElements[0].textContent).toContain("高风险");
    expect(riskElements[1].textContent).toContain("未评级");
  });

  it("renders search input and filters", () => {
    const { container } = renderCases();
    const inputs = container.querySelectorAll(".search-bar input[type='text']");
    expect(inputs.length).toBeGreaterThanOrEqual(1);
    const selects = container.querySelectorAll(".search-bar select");
    expect(selects.length).toBe(3);
  });

  it("calls onSearch when search button clicked", () => {
    const onSearch = vi.fn();
    const { container } = renderCases({ onSearch });
    const buttons = container.querySelectorAll(".search-bar button");
    // Last button is the search button
    const searchBtn = buttons[buttons.length - 1];
    fireEvent.click(searchBtn);
    expect(onSearch).toHaveBeenCalled();
  });

  it("calls onOpen when open button clicked", () => {
    const onOpen = vi.fn();
    renderCases({ onOpen });
    const openButtons = screen.getAllByText("打开");
    fireEvent.click(openButtons[0]);
    expect(onOpen).toHaveBeenCalledWith(1);
  });

  it("shows empty state when no cases", () => {
    renderCases({ cases: [] });
    expect(screen.getByText("还没有审核记录，请先新建一次合同审查。")).toBeTruthy();
  });

  it("shows issue count in case rows", () => {
    const { container } = renderCases();
    const issueElements = container.querySelectorAll(".case-issues");
    expect(issueElements[0].textContent).toContain("5");
    expect(issueElements[1].textContent).toContain("0");
  });
});
