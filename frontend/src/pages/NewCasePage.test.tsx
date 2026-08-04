import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getTask } from "../api/client";
import { NewCasePage } from "./NewCasePage";

vi.mock("../api/client", () => ({
  createCase: vi.fn(),
  getTask: vi.fn(),
  listCases: vi.fn(),
  reanalyzeAsync: vi.fn(),
  uploadCaseFile: vi.fn(),
}));

function makeFile(index: number): File {
  return new File(["材料 " + index], "事项材料-" + index + ".pdf", { type: "application/pdf" });
}

describe("NewCasePage", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    window.localStorage.clear();
  });

  it("allows at most four matter materials and removes one selection", () => {
    render(<NewCasePage onCreated={() => {}} />);

    const input = screen.getByLabelText(/事项签报 \/ 会议纪要文件/);
    expect(input.hasAttribute("multiple")).toBe(true);

    const files = [1, 2, 3, 4].map(makeFile);
    fireEvent.change(input, { target: { files } });
    expect(screen.getByText("已选择 4 份材料")).toBeTruthy();
    expect(screen.getByText("事项材料-4.pdf")).toBeTruthy();

    fireEvent.change(input, { target: { files: files.concat(makeFile(5)) } });
    expect(screen.getByText("最多上传 4 份事项签报或会议纪要。")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "移除事项材料-2.pdf" }));
    expect(screen.queryByText("事项材料-2.pdf")).toBeNull();
    expect(screen.getByText("已选择 3 份材料")).toBeTruthy();
  });

  it("appends matter materials selected in separate file picker actions", () => {
    render(<NewCasePage onCreated={() => {}} />);

    const input = screen.getByLabelText(/事项签报 \/ 会议纪要文件/);
    fireEvent.change(input, { target: { files: [makeFile(1), makeFile(2)] } });
    fireEvent.change(input, { target: { files: [makeFile(3), makeFile(4)] } });

    expect(screen.getByText("已选择 4 份材料")).toBeTruthy();
    expect(screen.getByText("事项材料-1.pdf")).toBeTruthy();
    expect(screen.getByText("事项材料-4.pdf")).toBeTruthy();
  });

  it("automatically resumes a persisted task after returning to the page", async () => {
    window.localStorage.setItem("contract-review-workbench.workspace", JSON.stringify({
      filters: {},
      newCaseDraft: {
        title: "合同审核",
        note: "",
        caseId: 12,
        activeStep: 3,
        uploadProgress: 100,
        taskProgress: { taskId: "task-12", progress: "正在审核", progressPercent: 60, currentStep: 3, totalSteps: 6 },
        fileNames: ["合同.pdf"],
        startedAt: "2026-08-04T00:00:00.000Z",
      },
    }));
    vi.mocked(getTask).mockResolvedValue({
      taskId: "task-12",
      status: "completed",
      result: null,
      error: null,
      progress: "审核完成",
      progressPercent: 100,
      currentStep: 6,
      totalSteps: 6,
      createdAt: "2026-08-04T00:00:00.000Z",
      startedAt: "2026-08-04T00:00:01.000Z",
      finishedAt: "2026-08-04T00:00:02.000Z",
    });
    const onCreated = vi.fn();

    render(<NewCasePage onCreated={onCreated} />);

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(12));
    expect(screen.getByText("审核任务已完成。")).toBeTruthy();
  });
});
