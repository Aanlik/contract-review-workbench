import { useEffect, useMemo, useState } from "react";

import type { Issue, ManualIssuePayload } from "../api/types";
import { AiChatPanel } from "../components/AiChatPanel";
import { EvidenceViewer } from "../components/EvidenceViewer";
import { IssueDetail } from "../components/IssueDetail";
import { IssueList } from "../components/IssueList";
import { loadWorkspaceState, saveWorkspaceState } from "../state/workspace";

const sampleIssues: Issue[] = [
  {
    id: 1,
    title: "法审晚于合同签订日期",
    issueType: "process_audit",
    source: "ai",
    riskLevel: "high",
    status: "pending",
    description: "OA 签报中的法务审核时间晚于合同签订日期，存在先签后审风险。",
    suggestion: "请核对合同实际签署时间，并补充法审前置审批证据。",
    evidenceRefs: [
      {
        id: 1,
        fileId: null,
        pageNumber: 3,
        ocrBlockId: null,
        originalText: "法务审核：2026-07-20；合同签订日期：2026-07-18",
        bbox: null,
        note: "日期比对异常",
        confidence: 0.92,
      },
    ],
  },
];

export function ReviewWorkspacePage() {
  const [issues, setIssues] = useState<Issue[]>(sampleIssues);
  const [selectedIssueId, setSelectedIssueId] = useState<number | undefined>(
    loadWorkspaceState().selectedIssueId ?? sampleIssues[0]?.id,
  );
  const selectedIssue = useMemo(
    () => issues.find((issue) => issue.id === selectedIssueId),
    [issues, selectedIssueId],
  );

  useEffect(() => {
    const state = loadWorkspaceState();
    saveWorkspaceState({ ...state, selectedIssueId });
  }, [selectedIssueId]);

  function createManualIssue(payload: ManualIssuePayload) {
    const next: Issue = {
      id: Math.max(0, ...issues.map((issue) => issue.id)) + 1,
      title: payload.title,
      issueType: "manual_mark",
      source: "manual",
      riskLevel: payload.riskLevel,
      status: "pending",
      description: payload.description,
      suggestion: payload.suggestion,
      evidenceRefs: payload.evidenceText
        ? [
            {
              id: Date.now(),
              fileId: null,
              pageNumber: null,
              ocrBlockId: null,
              originalText: payload.evidenceText,
              bbox: null,
              note: "人工标记",
              confidence: null,
            },
          ]
        : [],
    };
    setIssues((current) => [...current, next]);
    setSelectedIssueId(next.id);
  }

  return (
    <section className="workspace-grid">
      <aside className="issue-column">
        <IssueList issues={issues} selectedIssueId={selectedIssueId} onSelect={setSelectedIssueId} />
      </aside>
      <section className="evidence-column">
        <EvidenceViewer issue={selectedIssue} onCreateManualIssue={createManualIssue} />
      </section>
      <aside className="detail-column">
        <IssueDetail issue={selectedIssue} />
        <AiChatPanel scopeLabel={selectedIssue ? `当前问题：${selectedIssue.title}` : "任务级对话"} />
      </aside>
    </section>
  );
}
