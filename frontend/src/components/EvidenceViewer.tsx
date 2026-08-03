import { useEffect, useRef, useState } from "react";

import type { CaseDocument, EvidenceRef, Issue, ManualIssuePayload, UploadedFile } from "../api/types";

type EvidenceViewerProps = {
  issue?: Issue;
  documents: CaseDocument[];
  files: UploadedFile[];
  onCreateManualIssue: (payload: ManualIssuePayload) => void;
};

const riskColors: Record<string, string> = {
  high: "#dc3545",
  medium: "#ff9800",
  low: "#2196f3",
  info: "#6c757d",
};

const materialTypeLabels: Record<string, string> = {
  contract: "合同扫描件",
  legal_review_report: "法审签报",
  contract_approval: "合同签批文件",
  matter_report: "事项签报 / 会议纪要",
  sign_report: "历史签报",
  meeting_minutes: "历史会议纪要",
  approval: "历史审批材料",
};

function materialTypeLabel(fileType: string): string {
  return materialTypeLabels[fileType] ?? fileType;
}

function ConfidenceBadge({ confidence }: { confidence: number | null }) {
  if (confidence === null || confidence === undefined) return null;
  const percent = Math.round(confidence * 100);
  const color = percent >= 95 ? "#28a745" : percent >= 80 ? "#ff9800" : "#dc3545";
  return (
    <span className="confidence-badge" style={{ background: color }}>
      {percent}%
    </span>
  );
}

function BboxOverlay({
  blocks,
  highlightTexts,
  highlightBlockIds,
  pageWidth,
  pageHeight,
}: {
  blocks: { id: number; text: string; bbox: number[] | null; confidence: number | null }[];
  highlightTexts: string[];
  highlightBlockIds: Set<number>;
  pageWidth: number;
  pageHeight: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = pageWidth;
    canvas.height = pageHeight;
    ctx.clearRect(0, 0, pageWidth, pageHeight);

    // Draw all blocks lightly
    for (const block of blocks) {
      if (!block.bbox || block.bbox.length < 4) continue;
      const [x0, y0, x1, y1] = block.bbox;
      const isHighlighted =
        highlightBlockIds.has(block.id) ||
        highlightTexts.some((t) => t && block.text.includes(t));

      if (isHighlighted) {
        ctx.fillStyle = "rgba(255, 235, 59, 0.35)";
        ctx.strokeStyle = "#ff9800";
        ctx.lineWidth = 2;
        ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
        ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
      } else {
        ctx.strokeStyle = "rgba(0, 0, 0, 0.08)";
        ctx.lineWidth = 0.5;
        ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
      }
    }
  }, [blocks, highlightTexts, highlightBlockIds, pageWidth, pageHeight]);

  return (
    <canvas
      className="bbox-overlay"
      ref={canvasRef}
      style={{
        width: pageWidth,
        height: pageHeight,
        position: "absolute",
        top: 0,
        left: 0,
        pointerEvents: "none",
      }}
    />
  );
}

function EvidenceCard({ evidence }: { evidence: EvidenceRef }) {
  return (
    <div className="evidence-card">
      <div className="evidence-card-header">
        <b>页码</b> {evidence.pageNumber ?? "未关联"}
        <ConfidenceBadge confidence={evidence.confidence} />
      </div>
      <p className="evidence-text">{evidence.originalText ?? "暂无证据原文"}</p>
      {evidence.bbox && evidence.bbox.length >= 4 && (
        <small className="evidence-coords">
          位置: ({Math.round(evidence.bbox[0])}, {Math.round(evidence.bbox[1])}) → ({Math.round(evidence.bbox[2])}, {Math.round(evidence.bbox[3])})
        </small>
      )}
    </div>
  );
}

export function EvidenceViewer({ documents, files, issue, onCreateManualIssue }: EvidenceViewerProps) {
  const [evidenceText, setEvidenceText] = useState("");
  const [title, setTitle] = useState("人工新增问题");
  const [selectedPageId, setSelectedPageId] = useState<number | null>(null);
  const highlightedBlockIds = new Set(
    issue?.evidenceRefs
      ?.map((evidence) => evidence.ocrBlockId)
      .filter((id): id is number => typeof id === "number") ?? [],
  );
  const evidenceTexts: string[] = issue?.evidenceRefs?.map((evidence) => evidence.originalText).filter((t): t is string => typeof t === "string") ?? [];

  // Find the first page with evidence for preview
  const evidencePage = selectedPageId
    ? documents.flatMap((d) => d.pages).find((p) => p.id === selectedPageId)
    : issue?.evidenceRefs?.[0]?.pageNumber
      ? documents
          .flatMap((d) => d.pages)
          .find((p) => {
            const ref = issue?.evidenceRefs?.[0];
            return ref && p.pageNumber === ref.pageNumber;
          })
      : documents[0]?.pages[0];

  return (
    <div className="evidence-viewer">
      <header className="panel-header">
        <h2>合同与证据</h2>
        <button
          type="button"
          onClick={() => {
            onCreateManualIssue({
              title,
              riskLevel: "medium",
              description: "请补充人工标记说明",
              evidenceText: evidenceText || "用户手动选中的原文片段",
            });
            setEvidenceText("");
          }}
        >
          新增人工标记
        </button>
      </header>

      <div className="manual-mark-form">
        <input
          onChange={(event) => setTitle(event.target.value)}
          placeholder="人工问题标题"
          value={title}
        />
        <textarea
          onChange={(event) => setEvidenceText(event.target.value)}
          placeholder="粘贴或输入需要标记的合同/流程材料原文"
          value={evidenceText}
        />
      </div>

      <div className="material-list">
        <h3>上传材料</h3>
        {files.length ? (
          files.map((file) => (
            <div className="material-row" key={file.id}>
              <strong>{file.fileName}</strong>
              <span className="material-type">{materialTypeLabel(file.fileType)}</span>
              <span className={`parse-status status-${file.parseStatus}`}>{file.parseStatus}</span>
            </div>
          ))
        ) : (
          <p>暂无上传材料。</p>
        )}
      </div>

      {issue?.evidenceRefs?.length ? (
        <div className="evidence-refs">
          <h3>证据引用 ({issue.evidenceRefs.length})</h3>
          {issue.evidenceRefs.map((evidence) => (
            <div key={evidence.id} onClick={() => evidence.pageNumber && setSelectedPageId(
              documents.flatMap(d => d.pages).find(p => p.pageNumber === evidence.pageNumber)?.id ?? null
            )} style={{ cursor: evidence.pageNumber ? "pointer" : "default" }}>
              <EvidenceCard evidence={evidence} />
            </div>
          ))}
        </div>
      ) : (
        <div className="document-placeholder">选择问题后展示合同、签报或会议纪要中的证据位置。</div>
      )}

      {/* Page preview with bbox overlay */}
      {evidencePage && evidencePage.blocks.length > 0 && (
        <div className="page-preview">
          <h3>
            页面预览 — 第 {evidencePage.pageNumber} 页
            <span className="block-count">{evidencePage.blocks.length} 个文本块</span>
          </h3>
          <div className="page-canvas-container" style={{ position: "relative", width: "100%", maxWidth: 600, maxHeight: 400, overflow: "auto" }}>
            <BboxOverlay
              blocks={evidencePage.blocks}
              highlightTexts={evidenceTexts}
              highlightBlockIds={highlightedBlockIds}
              pageWidth={evidencePage.width ?? 595}
              pageHeight={evidencePage.height ?? 842}
            />
          </div>
          <div className="page-blocks">
            {evidencePage.blocks.map((block) => {
              const isHighlighted =
                highlightedBlockIds.has(block.id) ||
                evidenceTexts.some((text) => text && block.text.includes(text));
              return (
                <div
                  className={isHighlighted ? "block-item highlighted" : "block-item"}
                  data-testid={`evidence-block-${block.id}`}
                  key={block.id}
                >
                  <div className="block-header">
                    <span className="block-source">{block.source}</span>
                    <ConfidenceBadge confidence={block.confidence} />
                    {block.bbox && block.bbox.length >= 4 && (
                      <span className="block-coords">
                        [{Math.round(block.bbox[0])},{Math.round(block.bbox[1])}]
                      </span>
                    )}
                  </div>
                  <p className="block-text">{block.text}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Document text list */}
      <div className="document-text-list">
        <h3>解析原文</h3>
        {documents.length ? (
          documents.map((document) => (
            <details className="document-text" key={document.id} open={document.fileType === "contract"}>
              <summary>
                {document.fileName} · {materialTypeLabel(document.fileType)} · {document.parseStatus}
              </summary>
              {document.pages.length ? (
                document.pages.map((page) => (
                  <div className="page-text" key={page.id}>
                    <b>
                      第 {page.pageNumber} 页
                      <button
                        className="page-preview-btn"
                        onClick={() => setSelectedPageId(page.id)}
                        type="button"
                      >
                        预览
                      </button>
                    </b>
                    {page.blocks.map((block) => {
                      const isHighlighted =
                        highlightedBlockIds.has(block.id) ||
                        evidenceTexts.some((text) => text && block.text.includes(text));
                      return (
                        <p
                          className={isHighlighted ? "evidence-highlight" : ""}
                          data-testid={`evidence-block-${block.id}`}
                          key={block.id}
                        >
                          {block.text}
                          <ConfidenceBadge confidence={block.confidence} />
                        </p>
                      );
                    })}
                  </div>
                ))
              ) : (
                <p>暂无可展示文本块。</p>
              )}
            </details>
          ))
        ) : (
          <p>暂无解析原文。</p>
        )}
      </div>
    </div>
  );
}
