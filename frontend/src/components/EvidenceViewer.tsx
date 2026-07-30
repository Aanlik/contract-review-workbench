import { useState } from "react";

import type { CaseDocument, EvidenceRef, Issue, ManualIssuePayload, UploadedFile } from "../api/types";

type EvidenceViewerProps = {
  issue?: Issue;
  documents: CaseDocument[];
  files: UploadedFile[];
  onCreateManualIssue: (payload: ManualIssuePayload) => void;
};

function EvidenceCard({ evidence }: { evidence: EvidenceRef }) {
  return (
    <div className="evidence-card">
      <div>
        <b>页码</b> {evidence.pageNumber ?? "未关联"}
      </div>
      <p>{evidence.originalText ?? "暂无证据原文"}</p>
      <small>置信度：{evidence.confidence ?? "未提供"}</small>
    </div>
  );
}

export function EvidenceViewer({ documents, files, issue, onCreateManualIssue }: EvidenceViewerProps) {
  const [evidenceText, setEvidenceText] = useState("");
  const [title, setTitle] = useState("人工新增问题");
  const highlightedBlockIds = new Set(
    issue?.evidenceRefs
      ?.map((evidence) => evidence.ocrBlockId)
      .filter((id): id is number => typeof id === "number") ?? [],
  );
  const evidenceTexts = issue?.evidenceRefs?.map((evidence) => evidence.originalText).filter(Boolean) ?? [];

  return (
    <div>
      <header className="panel-header">
        <h2>合同与证据</h2>
        <button type="button" onClick={() => {
          onCreateManualIssue({
            title,
            riskLevel: "medium",
            description: "请补充人工标记说明",
            evidenceText: evidenceText || "用户手动选中的原文片段",
          });
          setEvidenceText("");
        }}>
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
              <span>{file.fileType}</span>
              <span>{file.parseStatus}</span>
            </div>
          ))
        ) : (
          <p>暂无上传材料。</p>
        )}
      </div>
      {issue?.evidenceRefs?.length ? (
        issue.evidenceRefs.map((evidence) => <EvidenceCard evidence={evidence} key={evidence.id} />)
      ) : (
        <div className="document-placeholder">选择问题后展示合同、签报或会议纪要中的证据位置。</div>
      )}
      <div className="document-text-list">
        <h3>解析原文</h3>
        {documents.length ? (
          documents.map((document) => (
            <details className="document-text" key={document.id} open={document.fileType === "contract"}>
              <summary>
                {document.fileName} · {document.fileType} · {document.parseStatus}
              </summary>
              {document.pages.length ? (
                document.pages.map((page) => (
                  <div className="page-text" key={page.id}>
                    <b>第 {page.pageNumber} 页</b>
                    {page.blocks.map((block) => (
                      <p
                        className={
                          highlightedBlockIds.has(block.id) ||
                          evidenceTexts.some((text) => text && block.text.includes(text))
                            ? "evidence-highlight"
                            : ""
                        }
                        data-testid={`evidence-block-${block.id}`}
                        key={block.id}
                      >
                        {block.text}
                      </p>
                    ))}
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
