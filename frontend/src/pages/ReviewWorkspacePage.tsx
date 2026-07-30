import { useEffect, useMemo, useState } from "react";

import {
  applyAiMessageAsNewIssue,
  applyAiMessageToIssue,
  createManualIssue,
  exportCase,
  getCaseChat,
  getIssueChat,
  listCaseDocuments,
  listCaseFiles,
  listIssues,
  reanalyzeCase,
  sendCaseChat,
  sendIssueChat,
  updateIssue,
} from "../api/client";
import type {
  AiMessage,
  CaseDocument,
  Issue,
  IssueUpdatePayload,
  ManualIssuePayload,
  UploadedFile,
} from "../api/types";
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
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [documents, setDocuments] = useState<CaseDocument[]>([]);
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
    if (!nextIssues.some((issue) => issue.id === selectedIssueId)) {
      setSelectedIssueId(nextIssues[0]?.id);
    }
  }

  async function refreshFiles() {
    setFiles(await listCaseFiles(caseId));
  }

  async function refreshDocuments() {
    setDocuments(await listCaseDocuments(caseId));
  }

  async function refreshChat() {
    const chat = selectedIssueId
      ? await getIssueChat(caseId, selectedIssueId)
      : await getCaseChat(caseId);
    setMessages(chat.messages);
  }

  useEffect(() => {
    refreshIssues().catch((error) => setStatus(error.message));
    refreshFiles().catch(() => setFiles([]));
    refreshDocuments().catch(() => setDocuments([]));
  }, [caseId]);

  useEffect(() => {
    refreshChat().catch(() => setMessages([]));
  }, [caseId, selectedIssueId]);

  async function handleCreateManualIssue(payload: ManualIssuePayload) {
    const next = await createManualIssue(caseId, payload);
    await refreshIssues();
    await refreshFiles();
    await refreshDocuments();
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

  async function handleApplyAsSuggestion(messageId: number) {
    if (!selectedIssue) {
      setStatus("请先选择一个问题，再应用为建议。");
      return;
    }
    const saved = await applyAiMessageToIssue(selectedIssue.id, messageId, "update_suggestion");
    setIssues((current) => current.map((issue) => (issue.id === saved.id ? saved : issue)));
    setStatus("AI 回复已应用为当前问题建议。");
  }

  async function handleApplyAsNewIssue(messageId: number) {
    const issue = await applyAiMessageAsNewIssue(messageId);
    await refreshIssues();
    setSelectedIssueId(issue.id);
    setStatus("AI 回复已应用为新问题。");
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
          <EvidenceViewer
            documents={documents}
            files={files}
            issue={selectedIssue}
            onCreateManualIssue={handleCreateManualIssue}
          />
        </section>
        <aside className="detail-column">
          <IssueDetail issue={selectedIssue} onReanalyze={handleReanalyze} onSave={handleSaveIssue} />
          <AiChatPanel
            messages={messages}
            onApplyAsNewIssue={handleApplyAsNewIssue}
            onApplyAsSuggestion={handleApplyAsSuggestion}
            onSend={handleSendChat}
            scopeLabel={selectedIssue ? `当前问题：${selectedIssue.title}` : "任务级对话"}
          />
        </aside>
      </section>
    </>
  );
}
