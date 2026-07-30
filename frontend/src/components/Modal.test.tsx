import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Modal, ConfirmDialog, ExportDialog } from "./Modal";

describe("Modal", () => {
  it("renders when open", () => {
    render(
      <Modal open onClose={() => {}} title="测试弹窗">
        <p>弹窗内容</p>
      </Modal>,
    );
    expect(screen.getByText("测试弹窗")).toBeTruthy();
    expect(screen.getByText("弹窗内容")).toBeTruthy();
  });

  it("does not render when closed", () => {
    const { container } = render(
      <Modal open={false} onClose={() => {}} title="测试弹窗">
        <p>弹窗内容</p>
      </Modal>,
    );
    expect(container.querySelector(".modal-overlay")).toBeNull();
  });

  it("calls onClose when close button clicked", () => {
    const onClose = vi.fn();
    const { container } = render(
      <Modal open onClose={onClose} title="测试">
        <p>内容</p>
      </Modal>,
    );
    const closeBtn = container.querySelector(".modal-close");
    expect(closeBtn).toBeTruthy();
    fireEvent.click(closeBtn!);
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose on Escape key", () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="测试">
        <p>内容</p>
      </Modal>,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});

describe("ConfirmDialog", () => {
  it("renders message and buttons", () => {
    render(
      <ConfirmDialog
        open
        onClose={() => {}}
        onConfirm={() => {}}
        title="确认删除"
        message="确定要删除吗？"
        confirmLabel="删除"
      />,
    );
    expect(screen.getByText("确认删除")).toBeTruthy();
    expect(screen.getByText("确定要删除吗？")).toBeTruthy();
    expect(screen.getByRole("button", { name: "删除" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "取消" })).toBeTruthy();
  });

  it("calls onConfirm and onClose when confirm clicked", () => {
    const onConfirm = vi.fn();
    const onClose = vi.fn();
    render(
      <ConfirmDialog
        open
        onClose={onClose}
        onConfirm={onConfirm}
        title="确认操作"
        message="确认吗？"
        confirmLabel="确定执行"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "确定执行" }));
    expect(onConfirm).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});

describe("ExportDialog", () => {
  it("renders scope and format selects", () => {
    render(<ExportDialog open onClose={() => {}} onExport={() => {}} />);
    expect(screen.getByText("导出审核报告")).toBeTruthy();
    expect(screen.getByText("导出范围")).toBeTruthy();
    expect(screen.getByText("导出格式")).toBeTruthy();
  });

  it("calls onExport with default values when form submitted", () => {
    const onExport = vi.fn();
    const onClose = vi.fn();
    const { container } = render(<ExportDialog open onClose={onClose} onExport={onExport} />);
    const form = container.querySelector("form");
    expect(form).toBeTruthy();
    fireEvent.submit(form!);
    expect(onExport).toHaveBeenCalledWith("final", "markdown");
    expect(onClose).toHaveBeenCalled();
  });
});
