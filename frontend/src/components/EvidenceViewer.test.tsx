import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EvidenceViewer } from "./EvidenceViewer";

describe("EvidenceViewer", () => {
  beforeEach(() => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("focuses the contract OCR block referenced by the selected issue", () => {
    const scrollIntoView = vi.fn();
    HTMLElement.prototype.scrollIntoView = scrollIntoView;

    render(
      <EvidenceViewer
        caseId={12}
        documents={[
          {
            id: 1,
            fileType: "matter_report",
            fileName: "事项签报.txt",
            parseMethod: "pdf_text",
            parseStatus: "parsed",
            pages: [
              {
                id: 10,
                pageNumber: 1,
                imagePath: null,
                width: null,
                height: null,
                hasTextLayer: true,
                ocrStatus: "completed",
                blocks: [],
              },
            ],
          },
          {
            id: 2,
            fileType: "contract",
            fileName: "合同.txt",
            parseMethod: "ocr",
            parseStatus: "parsed",
            pages: [
              {
                id: 20,
                pageNumber: 1,
                imagePath: null,
                width: null,
                height: null,
                hasTextLayer: false,
                ocrStatus: "completed",
                blocks: [],
              },
              {
                id: 21,
                pageNumber: 2,
                imagePath: null,
                width: null,
                height: null,
                hasTextLayer: false,
                ocrStatus: "completed",
                blocks: [
                  {
                    id: 200,
                    text: "合同签订日期：2025年10月14日",
                    bbox: [10, 20, 300, 40],
                    confidence: 0.98,
                    orderIndex: 0,
                    source: "ocr",
                  },
                ],
              },
            ],
          },
        ]}
        files={[]}
        focusRequest={{ issueId: 8, fileId: 2, pageNumber: 2, ocrBlockId: 200 }}
        issue={{
          id: 8,
          issueType: "process_audit",
          source: "system",
          riskLevel: "medium",
          title: "合同日期需要复核",
          status: "pending",
          evidenceRefs: [
            {
              id: 8,
              fileId: 2,
              pageNumber: 2,
              ocrBlockId: 200,
              originalText: "合同签订日期：2025年10月14日",
              bbox: [10, 20, 300, 40],
              note: null,
              confidence: 0.98,
            },
          ],
        }}
        onCreateManualIssue={() => {}}
      />,
    );

    expect(screen.getByText("已定位到合同第 2 页")).toBeTruthy();
    expect(screen.getAllByTestId("evidence-block-200").some((element) => element.className.includes("focused"))).toBe(true);
    expect(scrollIntoView.mock.calls.length).toBeGreaterThan(0);
  });

  it("underlines OCR blocks linked to the selected issue evidence", () => {
    render(
      <EvidenceViewer
        caseId={12}
        documents={[
          {
            id: 1,
            fileType: "contract",
            fileName: "合同.txt",
            parseMethod: "pdf_text",
            parseStatus: "parsed",
            pages: [
              {
                id: 1,
                pageNumber: 1,
                imagePath: null,
                width: null,
                height: null,
                hasTextLayer: true,
                ocrStatus: "completed",
                blocks: [
                  {
                    id: 9,
                    text: "甲方不得以任何理由解除本合同。",
                    bbox: [10, 20, 300, 40],
                    confidence: 0.95,
                    orderIndex: 0,
                    source: "pdf_text",
                  },
                ],
              },
            ],
          },
        ]}
        files={[]}
        issue={{
          id: 1,
          issueType: "contract_risk",
          source: "ai",
          riskLevel: "high",
          title: "解除权限制过严",
          status: "pending",
          evidenceRefs: [
            {
              id: 1,
              fileId: 1,
              pageNumber: 1,
              ocrBlockId: 9,
              originalText: "甲方不得以任何理由解除本合同。",
              bbox: null,
              note: null,
              confidence: 0.95,
            },
          ],
        }}
        onCreateManualIssue={() => {}}
      />,
    );

    // Block appears in both page preview and document text list
    const blocks = screen.getAllByTestId("evidence-block-9");
    expect(blocks.length).toBeGreaterThanOrEqual(1);
    // At least one should be highlighted
    expect(blocks.some((el) => el.className.includes("evidence-highlight"))).toBe(true);
  });

  it("renders the original page image and overlay mode controls", () => {
    render(
      <EvidenceViewer
        caseId={12}
        documents={[
          {
            id: 1,
            fileType: "contract",
            fileName: "扫描合同.pdf",
            parseMethod: "ocr",
            parseStatus: "parsed",
            pages: [
              {
                id: 1,
                pageNumber: 1,
                imagePath: "cases/12/pages/1/page-0001.png",
                width: 600,
                height: 800,
                hasTextLayer: false,
                ocrStatus: "completed",
                blocks: [
                  {
                    id: 11,
                    text: "合同标题",
                    bbox: [20, 30, 200, 60],
                    confidence: 0.98,
                    orderIndex: 0,
                    source: "ocr",
                  },
                ],
              },
            ],
          },
        ]}
        files={[]}
        onCreateManualIssue={() => {}}
      />,
    );

    expect(
      screen
        .getAllByTestId("evidence-page-image")
        .some((element) => element.getAttribute("src") === "/api/cases/12/documents/1/pages/1/image"),
    ).toBe(true);
    expect(screen.getAllByRole("button", { name: "仅显示问题框" }).length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("evidence-page-canvas").length).toBeGreaterThan(0);
  });

  it("switches materials and pages instead of showing only the contract first page", () => {
    render(
      <EvidenceViewer
        caseId={12}
        documents={[
          {
            id: 101,
            fileType: "contract",
            fileName: "合同.pdf",
            parseMethod: "ocr",
            parseStatus: "parsed",
            pages: [
              { id: 1011, pageNumber: 1, imagePath: null, width: 600, height: 800, hasTextLayer: false, ocrStatus: "completed", blocks: [] },
              { id: 1012, pageNumber: 2, imagePath: null, width: 600, height: 800, hasTextLayer: false, ocrStatus: "completed", blocks: [] },
            ],
          },
          {
            id: 102,
            fileType: "legal_review_report",
            fileName: "法审签报.pdf",
            parseMethod: "text",
            parseStatus: "parsed",
            pages: [
              { id: 1021, pageNumber: 1, imagePath: null, width: 600, height: 800, hasTextLayer: true, ocrStatus: "completed", blocks: [] },
              { id: 1022, pageNumber: 2, imagePath: null, width: 600, height: 800, hasTextLayer: true, ocrStatus: "completed", blocks: [] },
            ],
          },
        ]}
        files={[
          { id: 101, caseId: 12, fileType: "contract", fileName: "合同.pdf", parseStatus: "parsed" },
          { id: 102, caseId: 12, fileType: "legal_review_report", fileName: "法审签报.pdf", parseStatus: "parsed" },
        ]}
        onCreateManualIssue={() => {}}
      />,
    );

    fireEvent.click(screen.getByTestId("material-document-102"));
    expect(screen.getAllByTestId("evidence-preview-page").some((element) => element.textContent?.includes("第 1 页"))).toBe(true);
    fireEvent.click(screen.getByTestId("page-selector-102-2"));
    expect(screen.getAllByTestId("evidence-preview-page").some((element) => element.textContent?.includes("第 2 页"))).toBe(true);
  });

  it("shows a retry action for a failed OCR material", () => {
    const onRetryOcr = vi.fn();
    render(
      <EvidenceViewer
        caseId={12}
        documents={[
          {
            id: 3,
            fileType: "contract",
            fileName: "失败合同.pdf",
            parseMethod: "ocr",
            parseStatus: "ocr_failed",
            pages: [],
          },
        ]}
        files={[{ id: 3, caseId: 12, fileType: "contract", fileName: "失败合同.pdf", parseStatus: "ocr_failed" }]}
        onCreateManualIssue={() => {}}
        onRetryOcr={onRetryOcr}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "重新识别" }));
    expect(onRetryOcr).toHaveBeenCalledWith(3);
  });

  it("keeps retry status visible for every OCR task in progress", () => {
    render(
      <EvidenceViewer
        caseId={12}
        documents={[
          { id: 3, fileType: "contract", fileName: "合同.pdf", parseMethod: "ocr", parseStatus: "processing", pages: [] },
          { id: 4, fileType: "matter_report", fileName: "事项签报.pdf", parseMethod: "ocr", parseStatus: "processing", pages: [] },
        ]}
        files={[
          { id: 3, caseId: 12, fileType: "contract", fileName: "合同.pdf", parseStatus: "processing" },
          { id: 4, caseId: 12, fileType: "matter_report", fileName: "事项签报.pdf", parseStatus: "processing" },
        ]}
        onCreateManualIssue={() => {}}
        onRetryOcr={() => {}}
        retryingFileIds={new Set([3, 4])}
      />,
    );

    expect(screen.getAllByRole("button", { name: "识别中..." })).toHaveLength(2);
  });
});
