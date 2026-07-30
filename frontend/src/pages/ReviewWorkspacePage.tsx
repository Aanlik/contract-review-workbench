import { useEffect, useMemo, useState } from "react";

import {
  createManualIssue,
  exportCase,
  getCaseChat,
  listIssues,
  reanalyzeCase,
  sendCaseChat,
  sendIssueChat,
  updateIssue,
} from "../api/client";
import type { AiMessage, Issue, IssueUpdatePayload, ManualIssuePayload } from "../api/types";
import { AiChatPanel } from "../components/AiChatPanel";
import { EvidenceViewer } from "../components/EvidenceViewer";
import { IssueDetail } from "../components/IssueDetail";
import { IssueList } from "../components/IssueList";
import { loadWorkspaceState, saveWorkspaceState } from "../state/workspace";

type ReviewWorkspacePageProps = {
  caseId: number;
  onCaseChanged: () => void;
};

export function ReviewWorkspacePage({ caseId, onCaseChanged }: ReviewWorkspacePageProps) {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [status, setStatus] = useState("");
  const [selectedIssueId, setSelectedIssueId] = useState<number | undefined>(
    loadWorkspaceState().selectedIssueId,
  );
  const selectedIssue = useMemo(
    () => issues.find((issue) => issue.id === selectedIssueId),
    [issues, selectedIssueId],
  );

  useEffect(() => {
    const state = loadWorkspaceState();
    saveWorkspaceState({ ...state, selectedCaseId: caseId, selectedIssueId });
  }, [caseId, selectedIssueId]);

  async function refreshIssues() {
    const nextIssues = await listIssues(caseId);
    setIssues(nextIssues);
    if (!selectedIssueId && nextIssues[0]) setSelectedIssueId(nextIssues[0].id);
  }

  async function refreshChat() {
    const chat = await getCaseChat(caseId);
    setMessages(chat.messages);
  }

  useEffect(() => {
    refreshIssues().catch((error) => setStatus(error.message));
    refreshChat().catch(() => setMessages([]));
  }, [caseId]);

  async function handleCreateManualIssue(payload: ManualIssuePayload) {
    const next = await createManualIssue(caseId, payload);
    await refreshIssues();
    setSelectedIssueId(next.id);
  }

  async function handleSaveIssue(issueId: number, payload: IssueUpdatePayload) {
    const saved = await updateIssue(issueId, payload);
    setIssues((current) => current.map((issue) => (issue.id === saved.id ? saved : issue)));
    setStatus("问题已保存。");
  }

  async function handleReanalyze() {
    setStatus("正在重新审核...");
    await reanalyzeCase(caseId, selectedIssue ? `围绕问题重新分析：${selectedIssue.title}` : undefined);
    await refreshIssues();
    onCaseChanged();
    setStatus("重新审核完成。");
  }

  async function handleSendChat(message: string) {
    const chat = selectedIssue
      ? await sendIssueChat(caseId, selectedIssue.id, message)
      : await sendCaseChat(caseId, message);
    setMessages(chat.messages);
  }

  async function handleExport() {
    const result = await exportCase(caseId);
    setStatus(`报告已导出：${result.filePath}`);
  }

  return (
    <>
      <div className="workspace-actions">
        <button onClick={handleReanalyze} type="button">整份合同重新审核</button>
        <button onClick={handleExport} type="button">导出报告</button>
        {status && <span>{status}</span>}
      </div>
      <section className="workspace-grid">
        <aside className="issue-column">
          <IssueList issues={issues} selectedIssueId={selectedIssueId} onSelect={setSelectedIssueId} />
        </aside>
        <section className="evidence-column">
          <EvidenceViewer issue={selectedIssue} onCreateManualIssue={handleCreateManualIssue} />
        </section>
        <aside className="detail-column">
          <IssueDetail issue={selectedIssue} onReanalyze={handleReanalyze} onSave={handleSaveIssue} />
          <AiChatPanel
            messages={messages}
            onSend={handleSendChat}
            scopeLabel={selectedIssue ? `当前问题：${selectedIssue.title}` : "任务级对话"}
          />
        </aside>
      </section>
    </>
  );
}
