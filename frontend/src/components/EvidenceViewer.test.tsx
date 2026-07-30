import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidenceViewer } from "./EvidenceViewer";

describe("EvidenceViewer", () => {
  it("underlines OCR blocks linked to the selected issue evidence", () => {
    render(
      <EvidenceViewer
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
});
