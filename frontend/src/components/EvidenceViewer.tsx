import type { EvidenceRef, Issue, ManualIssuePayload } from "../api/types";

type EvidenceViewerProps = {
  issue?: Issue;
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

export function EvidenceViewer({ issue, onCreateManualIssue }: EvidenceViewerProps) {
  return (
    <div>
      <header className="panel-header">
        <h2>合同与证据</h2>
        <button
          type="button"
          onClick={() =>
            onCreateManualIssue({
              title: "人工新增问题",
              riskLevel: "medium",
              description: "请补充人工标记说明",
              evidenceText: "用户手动选中的原文片段",
            })
          }
        >
          新增人工标记
        </button>
      </header>
      {issue?.evidenceRefs?.length ? (
        issue.evidenceRefs.map((evidence) => <EvidenceCard evidence={evidence} key={evidence.id} />)
      ) : (
        <div className="document-placeholder">选择问题后展示合同、签报或会议纪要中的证据位置。</div>
      )}
    </div>
  );
}
