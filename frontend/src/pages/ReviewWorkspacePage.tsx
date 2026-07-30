import { useEffect, useMemo, useState } from "react";

import {
  applyAiMessageAsNewIssue,
  applyAiMessageToIssue,
  batchDeleteIssues,
  batchUpdateIssues,
  createManualIssue,
  downloadExport,
  exportCase,
  getCaseChat,
  getIssueChat,
  listCaseDocuments,
  listCaseFiles,
  listCaseVersions,
  listIssues,
  reanalyzeAsync,
  getTask,
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
  ReviewVersion,
  TaskStatus,
  UploadedFile,
} from "../api/types";
import { AiChatPanel } from "../components/AiChatPanel";
import { ConfirmDialog } from "../components/Modal";
import { EvidenceViewer } from "../components/EvidenceViewer";
import { IssueDetail } from "../components/IssueDetail";
import { IssueList } from "../components/IssueList";
import { VersionComparison } from "../components/VersionComparison";
import { loadWorkspaceState, saveWorkspaceState } from "../state/workspace";

type ReviewWorkspacePageProps = {
  caseId: number;
  onCaseChanged: () => void;
};

type WorkspaceTab = "issues" | "versions";

export function ReviewWorkspacePage({ caseId, onCaseChanged }: ReviewWorkspacePageProps) {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [documents, setDocuments] = useState<CaseDocument[]>([]);
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [versions, setVersions] = useState<ReviewVersion[]>([]);
  const [status, setStatus] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>(loadWorkspaceState().filters);
  const [selectedIssueId, setSelectedIssueId] = useState<number | undefined>(
    loadWorkspaceState().selectedIssueId,
  );
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("issues");
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const [exportFormat, setExportFormat] = useState<"markdown" | "docx" | "pdf">("markdown");
  const [exportScope, setExportScope] = useState<"final" | "all" | "high_and_medium" | "confirmed">("final");
  const [batchDeleteTarget, setBatchDeleteTarget] = useState<number[] | null>(null);

  const selectedIssue = useMemo(
    () => issues.find((issue) => issue.id === selectedIssueId),
    [issues, selectedIssueId],
  );

  useEffect(() => {
    const state = loadWorkspaceState();
    saveWorkspaceState({ ...state, filters, selectedCaseId: caseId, selectedIssueId });
  }, [caseId, filters, selectedIssueId]);

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

  async function refreshVersions() {
    setVersions(await listCaseVersions(caseId));
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
    refreshVersions().catch(() => setVersions([]));
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
    await updateIssue(issueId, payload);
    await refreshIssues();
    onCaseChanged();
  }

  async function handleReanalyze() {
    setIsReanalyzing(true);
    setStatus("正在提交审核任务...");
    try {
      const { taskId } = await reanalyzeAsync(caseId);
      setStatus("审核任务已提交，正在后台处理...");

      // Poll for progress
      const result = await new Promise<TaskStatus>((resolve, reject) => {
        const interval = setInterval(async () => {
          try {
            const task = await getTask(taskId);
            if (task.progress) setStatus(task.progress);
            if (task.status === "completed" || task.status === "failed") {
              clearInterval(interval);
              if (task.status === "failed") {
                reject(new Error(task.error || "审核失败"));
              } else {
                resolve(task);
              }
            }
          } catch (err) {
            clearInterval(interval);
            reject(err);
          }
        }, 1000);
      });

      await refreshIssues();
      await refreshVersions();
      onCaseChanged();
      setStatus(`重新审核完成。发现 ${((result.result as any)?.issue_count) ?? "?"} 个问题。`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "重新审核失败。");
    } finally {
      setIsReanalyzing(false);
    }
  }

  async function handleSendChat(message: string) {
    const conversation = selectedIssueId
      ? await sendIssueChat(caseId, selectedIssueId, message)
      : await sendCaseChat(caseId, message);
    setMessages(conversation.messages);
  }

  async function handleApplySuggestion(messageId: number) {
    if (selectedIssueId) {
      await applyAiMessageToIssue(selectedIssueId, messageId, "update_suggestion");
      await refreshIssues();
    }
  }

  async function handleApplyAsNewIssue(messageId: number) {
    await applyAiMessageAsNewIssue(messageId);
    await refreshIssues();
  }

  async function handleBatchUpdate(issueIds: number[], updates: { status?: string; riskLevel?: string }) {
    await batchUpdateIssues(issueIds, updates);
    await refreshIssues();
    onCaseChanged();
  }

  async function handleBatchDelete(issueIds: number[]) {
    setBatchDeleteTarget(issueIds);
  }

  async function confirmBatchDelete() {
    if (!batchDeleteTarget) return;
    await batchDeleteIssues(batchDeleteTarget);
    setBatchDeleteTarget(null);
    await refreshIssues();
    onCaseChanged();
  }

  async function handleExport() {
    try {
      setStatus("正在导出...");
      const result = await exportCase(caseId, exportScope, exportFormat);
      await downloadExport(result.filePath);
      setStatus("报告已导出并开始下载。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "导出失败");
    }
  }

  return (
    <section className="workspace">
      <header className="workspace-header">
        <div className="workspace-tabs">
          <button
            className={activeTab === "issues" ? "active" : ""}
            onClick={() => setActiveTab("issues")}
            type="button"
          >
            问题审核
          </button>
          <button
            className={activeTab === "versions" ? "active" : ""}
            onClick={() => setActiveTab("versions")}
            type="button"
          >
            版本对比
          </button>
        </div>
        <div className="workspace-actions">
          <button disabled={isReanalyzing} onClick={handleReanalyze} type="button">
            {isReanalyzing ? "审核中..." : "重新分析"}
          </button>
          <select onChange={(e) => setExportScope(e.target.value as any)} value={exportScope}>
            <option value="final">最终版</option>
            <option value="all">全部</option>
            <option value="high_and_medium">高+中风险</option>
            <option value="confirmed">已确认</option>
          </select>
          <select onChange={(e) => setExportFormat(e.target.value as any)} value={exportFormat}>
            <option value="markdown">Markdown</option>
            <option value="docx">Word (DOCX)</option>
            <option value="pdf">PDF/HTML</option>
          </select>
          <button onClick={handleExport} type="button">导出报告</button>
        </div>
        {status && <p className="workspace-status">{status}</p>}
      </header>

      {activeTab === "issues" && (
        <div className="workspace-layout">
          <div className="workspace-left">
            <IssueList
              filters={filters}
              issues={issues}
              selectedIssueId={selectedIssueId}
              onBatchDelete={handleBatchDelete}
              onBatchUpdate={handleBatchUpdate}
              onFilterChange={setFilters}
              onSelect={setSelectedIssueId}
            />
          </div>
          <div className="workspace-center">
            <IssueDetail
              issue={selectedIssue}
              onSave={handleSaveIssue}
              onReanalyze={handleReanalyze}
            />
            <EvidenceViewer
              documents={documents}
              files={files}
              issue={selectedIssue}
              onCreateManualIssue={handleCreateManualIssue}
            />
          </div>
          <div className="workspace-right">
            <AiChatPanel
              messages={messages}
              onApplyAsNewIssue={handleApplyAsNewIssue}
              onApplyAsSuggestion={handleApplySuggestion}
              onSend={handleSendChat}
              scopeLabel={selectedIssue ? `问题: ${selectedIssue.title}` : "整份合同"}
            />
          </div>
        </div>
      )}

      {activeTab === "versions" && (
        <div className="workspace-versions">
          <VersionComparison caseId={caseId} />
        </div>
      )}
      <ConfirmDialog
        danger
        message={`确认删除选中的 ${batchDeleteTarget?.length ?? 0} 个问题吗？此操作不可撤销。`}
        onClose={() => setBatchDeleteTarget(null)}
        onConfirm={confirmBatchDelete}
        open={batchDeleteTarget !== null}
        title="批量删除问题"
        confirmLabel="删除"
      />
    </section>
  );
}
