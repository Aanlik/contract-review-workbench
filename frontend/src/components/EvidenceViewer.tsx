import { useEffect, useRef, useState, type MouseEvent } from "react";

import { documentPageImageUrl } from "../api/client";
import type { CaseDocument, EvidenceRef, Issue, ManualIssuePayload, UploadedFile } from "../api/types";
import { labelOf, materialTypeLabels, parseSourceLabels, parseStatusLabels } from "../ui/labels";

type EvidenceViewerProps = {
  caseId: number;
  issue?: Issue;
  documents: CaseDocument[];
  files: UploadedFile[];
  onCreateManualIssue: (payload: ManualIssuePayload) => void;
  onRetryOcr?: (fileId: number) => void;
  retryingFileIds?: Set<number>;
  focusRequest?: {
    issueId?: number;
    fileId?: number | null;
    pageNumber?: number | null;
    ocrBlockId?: number | null;
  };
};

const riskColors: Record<string, string> = {
  high: "#dc3545",
  medium: "#ff9800",
  low: "#2196f3",
  info: "#6c757d",
};

function materialTypeLabel(fileType: string): string {
  return labelOf(materialTypeLabels, fileType, "其他材料");
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
  showAllBlocks,
  onBlockClick,
}: {
  blocks: { id: number; text: string; bbox: number[] | null; confidence: number | null }[];
  highlightTexts: string[];
  highlightBlockIds: Set<number>;
  pageWidth: number;
  pageHeight: number;
  showAllBlocks: boolean;
  onBlockClick: (blockId: number) => void;
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

    // Draw all OCR blocks lightly, or only the issue-linked blocks in focused mode.
    for (const block of blocks) {
      if (!block.bbox || block.bbox.length < 4) continue;
      const [x0, y0, x1, y1] = block.bbox;
      const isHighlighted =
        highlightBlockIds.has(block.id) ||
        highlightTexts.some((t) => t && block.text.includes(t));
      if (!showAllBlocks && !isHighlighted) continue;

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
  }, [blocks, highlightTexts, highlightBlockIds, pageWidth, pageHeight, showAllBlocks]);

  function handleClick(event: MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const x = ((event.clientX - rect.left) / rect.width) * pageWidth;
    const y = ((event.clientY - rect.top) / rect.height) * pageHeight;
    const matched = [...blocks].reverse().find((block) => {
      if (!block.bbox || block.bbox.length < 4) return false;
      const [x0, y0, x1, y1] = block.bbox;
      const isHighlighted =
        highlightBlockIds.has(block.id) ||
        highlightTexts.some((text) => text && block.text.includes(text));
      return (showAllBlocks || isHighlighted) && x >= x0 && x <= x1 && y >= y0 && y <= y1;
    });
    if (matched) onBlockClick(matched.id);
  }

  return (
    <canvas
      className="bbox-overlay"
      ref={canvasRef}
      data-testid="evidence-page-canvas"
      onClick={handleClick}
      style={{
        width: "100%",
        height: "100%",
        position: "absolute",
        top: 0,
        left: 0,
        pointerEvents: blocks.some((block) => block.bbox?.length === 4) ? "auto" : "none",
        cursor: blocks.some((block) => block.bbox?.length === 4) ? "crosshair" : "default",
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

export function EvidenceViewer({ caseId, documents, files, issue, onCreateManualIssue, onRetryOcr, retryingFileIds, focusRequest }: EvidenceViewerProps) {
  const [evidenceText, setEvidenceText] = useState("");
  const [title, setTitle] = useState("人工新增问题");
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [selectedPageId, setSelectedPageId] = useState<number | null>(null);
  const [focusStatus, setFocusStatus] = useState("");
  const [selectedBlockId, setSelectedBlockId] = useState<number | null>(null);
  const [showAllBlocks, setShowAllBlocks] = useState(true);
  const [pageImageFailed, setPageImageFailed] = useState(false);
  const [pageImageSize, setPageImageSize] = useState<{ width: number; height: number } | null>(null);
  const evidenceRef = issue?.evidenceRefs?.[0];
  const requestedFileId = focusRequest?.fileId ?? evidenceRef?.fileId;
  const requestedPageNumber = focusRequest?.pageNumber ?? evidenceRef?.pageNumber;
  const focusedBlockId = focusRequest?.ocrBlockId ?? evidenceRef?.ocrBlockId;
  const selectedDocument =
    documents.find((document) => document.id === selectedDocumentId) ??
    documents.find((document) => document.id === requestedFileId) ??
    documents.find((document) => document.fileType === "contract") ??
    documents[0];
  const materialFiles: UploadedFile[] = files.length
    ? files
    : documents.map((document) => ({
        id: document.id,
        caseId,
        fileType: document.fileType,
        fileName: document.fileName,
        parseStatus: document.parseStatus,
      }));

  useEffect(() => {
    if (!documents.length) return;
    const targetDocument =
      documents.find((document) => document.id === requestedFileId) ??
      documents.find((document) => document.id === selectedDocumentId) ??
      documents.find((document) => document.fileType === "contract") ??
      documents[0];
    const targetPage = targetDocument?.pages.find((page) => page.pageNumber === requestedPageNumber) ?? targetDocument?.pages[0];
    setSelectedDocumentId(targetDocument?.id ?? null);
    setSelectedPageId(targetPage?.id ?? null);
    if (!focusRequest && !evidenceRef) {
      setFocusStatus("");
    } else if (!requestedFileId && !requestedPageNumber && !focusedBlockId) {
      setFocusStatus("暂无具体证据定位，已打开合同识别内容。");
    } else if (targetDocument?.fileType === "contract" && targetPage) {
      setFocusStatus(`已定位到合同第 ${targetPage.pageNumber} 页`);
    } else if (targetPage) {
      setFocusStatus(`已定位到材料第 ${targetPage.pageNumber} 页`);
    } else {
      setFocusStatus("暂无具体证据定位。");
    }
  }, [documents, evidenceRef?.fileId, evidenceRef?.pageNumber, evidenceRef?.ocrBlockId, focusRequest?.issueId, focusRequest?.fileId, focusRequest?.pageNumber, focusRequest?.ocrBlockId, requestedFileId, requestedPageNumber, focusedBlockId, selectedDocumentId]);

  useEffect(() => {
    if (focusedBlockId === null || focusedBlockId === undefined) return;
    const target = document.querySelector(`[data-testid="evidence-block-${focusedBlockId}"]`);
    if (target instanceof HTMLElement && typeof target.scrollIntoView === "function") {
      target.scrollIntoView({ block: "center" });
    }
  }, [focusedBlockId, selectedDocumentId, selectedPageId]);

  const highlightedBlockIds = new Set(
    issue?.evidenceRefs
      ?.map((evidence) => evidence.ocrBlockId)
      .filter((id): id is number => typeof id === "number") ?? [],
  );
  const evidenceTexts: string[] = issue?.evidenceRefs?.map((evidence) => evidence.originalText).filter((t): t is string => typeof t === "string") ?? [];

  // The selected issue controls the document and page shown in the preview.
  const evidencePage = selectedPageId
    ? selectedDocument?.pages.find((page) => page.id === selectedPageId)
    : selectedDocument?.pages.find((page) => page.pageNumber === requestedPageNumber) ?? selectedDocument?.pages[0];

  const pageWidth = evidencePage?.width ?? pageImageSize?.width ?? 595;
  const pageHeight = evidencePage?.height ?? pageImageSize?.height ?? 842;
  const pageImageUrl = selectedDocument && evidencePage
    ? documentPageImageUrl(caseId, selectedDocument.id, evidencePage.pageNumber)
    : null;

  useEffect(() => {
    setPageImageFailed(false);
    setPageImageSize(null);
  }, [pageImageUrl]);

  function focusEvidence(evidence: EvidenceRef) {
    const targetDocument =
      documents.find((document) => document.id === evidence.fileId) ??
      documents.find((document) => document.fileType === "contract") ??
      documents[0];
    const targetPage = targetDocument?.pages.find((page) => page.pageNumber === evidence.pageNumber);
    setSelectedDocumentId(targetDocument?.id ?? null);
    setSelectedPageId(targetPage?.id ?? null);
  }

  function selectDocument(documentId: number) {
    const targetDocument = documents.find((document) => document.id === documentId);
    setSelectedDocumentId(documentId);
    setSelectedPageId(targetDocument?.pages[0]?.id ?? null);
    setSelectedBlockId(null);
  }

  function selectPage(documentId: number, pageId: number) {
    setSelectedDocumentId(documentId);
    setSelectedPageId(pageId);
    setSelectedBlockId(null);
  }

  function focusBlock(blockId: number) {
    setSelectedBlockId(blockId);
    const target = document.querySelector(`[data-testid="evidence-block-${blockId}"]`);
    if (target instanceof HTMLElement && typeof target.scrollIntoView === "function") {
      target.scrollIntoView({ block: "center" });
    }
  }

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
      {focusStatus && (
        <p className="evidence-focus-status" data-testid="evidence-focus-status">
          {focusStatus}
        </p>
      )}

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
        {materialFiles.length ? (
          materialFiles.map((file) => {
            const document = documents.find((item) => item.id === file.id);
            const parseStatus = document?.parseStatus ?? file.parseStatus;
            const isRetrying = retryingFileIds?.has(file.id) ?? false;
            const canRetry = onRetryOcr && (["ocr_failed", "needs_ocr"].includes(parseStatus) || isRetrying);
            return (
            <div className={`material-row${selectedDocument?.id === file.id ? " active" : ""}`} key={file.id}>
              <button
                className="material-select"
                data-testid={`material-document-${file.id}`}
                onClick={() => selectDocument(file.id)}
                type="button"
              >
                <strong>{file.fileName}</strong>
                <span className="material-type">{materialTypeLabel(file.fileType)}</span>
                <span className="material-pages">{document?.pages.length ? `${document.pages.length} 页` : "暂无页面"}</span>
                <span className={`parse-status status-${parseStatus}`}>{labelOf(parseStatusLabels, parseStatus)}</span>
              </button>
              {canRetry && (
                <button
                  className="material-retry"
                  disabled={isRetrying}
                  onClick={() => onRetryOcr(file.id)}
                  type="button"
                >
                  {isRetrying ? "识别中..." : "重新识别"}
                </button>
              )}
            </div>
            );
          })
        ) : (
          <p>暂无上传材料。</p>
        )}
      </div>

      {selectedDocument && selectedDocument.pages.length > 0 && (
        <div className="document-page-nav" data-testid="document-page-nav">
          <span className="document-page-nav-label">当前材料页面</span>
          <div className="document-page-buttons">
            {selectedDocument.pages.map((page) => (
              <button
                aria-pressed={evidencePage?.id === page.id}
                data-testid={`page-selector-${selectedDocument.id}-${page.pageNumber}`}
                key={page.id}
                onClick={() => selectPage(selectedDocument.id, page.id)}
                type="button"
              >
                第 {page.pageNumber} 页
              </button>
            ))}
          </div>
        </div>
      )}

      {selectedDocument && selectedDocument.pages.length === 0 && (
        <div className="document-placeholder" data-testid="document-preview-empty">
          当前材料暂无可预览页面。若扫描识别失败，请点击上方“重新识别”。
        </div>
      )}

      {issue?.evidenceRefs?.length ? (
        <div className="evidence-refs">
          <h3>证据引用 ({issue.evidenceRefs.length})</h3>
          {issue.evidenceRefs.map((evidence) => (
            <div key={evidence.id} onClick={() => focusEvidence(evidence)} style={{ cursor: evidence.pageNumber ? "pointer" : "default" }}>
              <EvidenceCard evidence={evidence} />
            </div>
          ))}
        </div>
      ) : (
        <div className="document-placeholder">选择问题后展示合同、签报或会议纪要中的证据位置。</div>
      )}

      {/* Page preview with bbox overlay */}
      {evidencePage && (evidencePage.blocks.length > 0 || pageImageUrl) && (
        <div className="page-preview">
          <h3 data-testid="evidence-preview-page">
            页面预览 — 第 {evidencePage.pageNumber} 页
            <span className="block-count">{evidencePage.blocks.length} 个文本块</span>
          </h3>
          <div className="page-preview-actions">
            <button type="button" onClick={() => setShowAllBlocks(true)} aria-pressed={showAllBlocks}>
              显示全部识别框
            </button>
            <button type="button" onClick={() => setShowAllBlocks(false)} aria-pressed={!showAllBlocks}>
              仅显示问题框
            </button>
          </div>
          <div className="page-canvas-container" style={{ position: "relative", width: "100%", maxWidth: 600, maxHeight: 640, overflow: "auto" }}>
            <div className="page-canvas-stage" style={{ position: "relative", width: "100%", aspectRatio: `${pageWidth} / ${pageHeight}` }}>
              {pageImageUrl && !pageImageFailed ? (
                <img
                  alt={`原文第 ${evidencePage.pageNumber} 页`}
                  className="original-page-image"
                  data-testid="evidence-page-image"
                  onLoad={(event) => {
                    setPageImageFailed(false);
                    const image = event.currentTarget;
                    if (image.naturalWidth > 0 && image.naturalHeight > 0) {
                      setPageImageSize({ width: image.naturalWidth, height: image.naturalHeight });
                    }
                  }}
                  onError={() => setPageImageFailed(true)}
                  src={pageImageUrl}
                />
              ) : (
                <div className="page-image-fallback" data-testid="evidence-page-image-fallback">
                  原文页面图暂不可用，以下显示 OCR 识别框。
                </div>
              )}
            <BboxOverlay
              blocks={evidencePage.blocks}
              highlightTexts={evidenceTexts}
              highlightBlockIds={highlightedBlockIds}
              onBlockClick={focusBlock}
              pageHeight={pageHeight}
              pageWidth={pageWidth}
              showAllBlocks={showAllBlocks}
            />
            </div>
          </div>
          <div className="page-blocks">
            {evidencePage.blocks.map((block) => {
              const isFocused = (selectedBlockId ?? focusedBlockId) === block.id;
              const isHighlighted =
                highlightedBlockIds.has(block.id) ||
                evidenceTexts.some((text) => text && block.text.includes(text));
              return (
                <div
                  className={`${isHighlighted ? "block-item highlighted" : "block-item"}${isFocused ? " focused" : ""}`}
                  data-testid={`evidence-block-${block.id}`}
                  key={block.id}
                >
                  <div className="block-header">
                    <span className="block-source">{labelOf(parseSourceLabels, block.source)}</span>
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
            <details className="document-text" key={document.id} open={document.id === selectedDocument?.id || (!selectedDocument && document.fileType === "contract")}>
              <summary>
                {document.fileName} · {materialTypeLabel(document.fileType)} · {labelOf(parseStatusLabels, document.parseStatus)}
              </summary>
              {document.pages.length ? (
                document.pages.map((page) => (
                  <div className="page-text" key={page.id}>
                    <b>
                      第 {page.pageNumber} 页
                      <button
                        className="page-preview-btn"
                        onClick={() => selectPage(document.id, page.id)}
                        type="button"
                      >
                        预览
                      </button>
                    </b>
                    {page.blocks.map((block) => {
                      const isFocused =
                        (selectedBlockId ?? focusedBlockId) === block.id && document.id === selectedDocument?.id;
                      const isHighlighted =
                        highlightedBlockIds.has(block.id) ||
                        evidenceTexts.some((text) => text && block.text.includes(text));
                      return (
                        <p
                          className={`${isHighlighted ? "evidence-highlight" : ""}${isFocused ? " focused" : ""}`}
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
