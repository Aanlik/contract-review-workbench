import { FormEvent, useEffect, useRef, useState } from "react";

import { createCase, getTask, listCases, reanalyzeAsync, uploadCaseFile, type UploadProgressCallback } from "../api/client";
import type { TaskStatus } from "../api/types";
import { loadWorkspaceState, saveWorkspaceState } from "../state/workspace";

type NewCasePageProps = {
  onCreated: (caseId: number) => void;
};

const PROGRESS_STEPS = [
  "文件上传",
  "加载材料和解析文本",
  "流程合规审计",
  "OCR 识别检查",
  "AI 合同法律风险审查",
  "生成审核结果",
];

export function NewCasePage({ onCreated }: NewCasePageProps) {
  const savedDraft = loadWorkspaceState().newCaseDraft;
  const [title, setTitle] = useState(savedDraft?.title ?? "");
  const [note, setNote] = useState(savedDraft?.note ?? "");
  const [contract, setContract] = useState<File | null>(null);
  const [legalReviewReport, setLegalReviewReport] = useState<File | null>(null);
  const [contractApproval, setContractApproval] = useState<File | null>(null);
  const [matterMaterial, setMatterMaterial] = useState<File | null>(null);
  const [status, setStatus] = useState("");
  const [activeStep, setActiveStep] = useState(savedDraft?.activeStep ?? -1);
  const [uploadProgress, setUploadProgress] = useState(savedDraft?.uploadProgress ?? 0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [taskProgress, setTaskProgress] = useState<TaskStatus | null>(null);
  const [resumedCaseId, setResumedCaseId] = useState<number | undefined>(savedDraft?.caseId);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Offer resume if draft exists
  const [showResume, setShowResume] = useState(!!savedDraft && savedDraft.activeStep >= 0);

  function persistDraft(step: number, caseId?: number, taskId?: string, taskProg?: TaskStatus) {
    const state = loadWorkspaceState();
    saveWorkspaceState({
      ...state,
      newCaseDraft: {
        title,
        note,
        caseId,
        activeStep: step,
        uploadProgress,
        taskProgress: taskId && taskProg ? {
          taskId,
          progress: taskProg.progress,
          progressPercent: taskProg.progressPercent,
          currentStep: taskProg.currentStep,
          totalSteps: taskProg.totalSteps,
        } : savedDraft?.taskProgress,
        fileNames: [contract?.name, legalReviewReport?.name, contractApproval?.name, matterMaterial?.name].filter(Boolean) as string[],
        startedAt: savedDraft?.startedAt ?? new Date().toISOString(),
      },
    });
  }

  function clearDraft() {
    const state = loadWorkspaceState();
    const { newCaseDraft, ...rest } = state;
    saveWorkspaceState(rest);
  }

  function stopPolling() {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }

  async function pollTask(taskId: string, caseId: number): Promise<TaskStatus> {
    return new Promise((resolve, reject) => {
      pollingRef.current = setInterval(async () => {
        try {
          const task = await getTask(taskId);
          setTaskProgress(task);
          if (task.currentStep > 0) setActiveStep(task.currentStep);
          if (task.progress) setStatus(task.progress);
          persistDraft(task.currentStep > 0 ? task.currentStep : activeStep, caseId, taskId, task);
          if (task.status === "completed" || task.status === "failed") {
            stopPolling();
            if (task.status === "failed") reject(new Error(task.error || "审核任务失败"));
            else resolve(task);
          }
        } catch (error) {
          stopPolling();
          reject(error);
        }
      }, 800);
    });
  }

  // Resume polling for an in-progress task
  async function handleResume() {
    setShowResume(false);
    if (!savedDraft?.caseId) {
      // No case created yet, just restore form state
      setStatus("已恢复表单内容，请重新提交。");
      return;
    }

    const caseId = savedDraft.caseId;
    setResumedCaseId(caseId);
    setIsSubmitting(true);

    // Check if there's a task to resume polling
    if (savedDraft.taskProgress?.taskId) {
      try {
        setStatus("正在恢复审核进度...");
        setActiveStep(savedDraft.activeStep);
        const taskId = savedDraft.taskProgress.taskId;
        const task = await getTask(taskId);
        if (task.status === "completed") {
          setActiveStep(6);
          setStatus("审核任务已完成。");
          clearDraft();
          onCreated(caseId);
          return;
        }
        if (task.status === "failed") {
          setStatus(`上次审核失败: ${task.error || "未知错误"}。请重新提交。`);
          setIsSubmitting(false);
          return;
        }
        // Still running, resume polling
        setTaskProgress(task);
        await pollTask(taskId, caseId);
        setActiveStep(6);
        setStatus("审核任务已完成。");
        clearDraft();
        onCreated(caseId);
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "恢复失败，请重新提交。");
        setIsSubmitting(false);
      }
    } else {
      // Case created but no task yet (shouldn't happen, but handle gracefully)
      setStatus("审核任务状态未知，请重新提交审核。");
      setIsSubmitting(false);
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) { setStatus("请先填写合同名称。"); return; }
    if (!contract) { setStatus("请上传合同扫描件。"); return; }
    if (!legalReviewReport) { setStatus("请上传法审签报 PDF。"); return; }
    if (!contractApproval) { setStatus("请上传合同签批文件 PDF。"); return; }
    setIsSubmitting(true);
    setTaskProgress(null);
    try {
      setActiveStep(0);
      setUploadProgress(0);
      setStatus("正在创建审核任务...");
      const reviewCase = await createCase({ title, note });
      setResumedCaseId(reviewCase.id);
      persistDraft(0, reviewCase.id);

      const onProgress: UploadProgressCallback = (percent) => setUploadProgress(percent);

      setStatus(`正在上传合同: ${contract.name}...`);
      setUploadProgress(0);
      await uploadCaseFile(reviewCase.id, "contract", contract, onProgress);
      persistDraft(1, reviewCase.id);

      setStatus(`正在上传法审签报: ${legalReviewReport.name}...`);
      setUploadProgress(0);
      await uploadCaseFile(reviewCase.id, "legal_review_report", legalReviewReport, onProgress);

      setStatus(`正在上传合同签批文件: ${contractApproval.name}...`);
      setUploadProgress(0);
      await uploadCaseFile(reviewCase.id, "contract_approval", contractApproval, onProgress);

      if (matterMaterial) {
        setStatus(`正在上传事项签报/会议纪要: ${matterMaterial.name}...`);
        setUploadProgress(0);
        await uploadCaseFile(reviewCase.id, "matter_report", matterMaterial, onProgress);
      }

      setUploadProgress(100);
      setActiveStep(1);
      setStatus("文件上传完成，正在启动 AI 审核...");

      const { taskId } = await reanalyzeAsync(reviewCase.id, note || "首次审核");
      setStatus("审核任务已提交，正在后台处理...");
      persistDraft(1, reviewCase.id, taskId);

      await pollTask(taskId, reviewCase.id);
      setActiveStep(6);
      setStatus("审核任务已完成。");
      clearDraft();
      onCreated(reviewCase.id);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "任务创建失败，请重试。");
    } finally {
      stopPolling();
      setIsSubmitting(false);
    }
  }

  useEffect(() => () => stopPolling(), []);

  return (
    <section className="new-case-page">
      <header className="page-header">
        <div>
          <p className="section-kicker">Upload & Analyze</p>
          <h1>新建审核</h1>
        </div>
      </header>

      {showResume && (
        <div className="resume-banner">
          <p>
            检测到上次未完成的审核任务
            {savedDraft?.title ? `「${savedDraft.title}」` : ""}
            {savedDraft?.fileNames?.length ? `，已上传 ${savedDraft.fileNames.length} 个文件` : ""}
            {savedDraft?.taskProgress?.progress ? `，进度：${savedDraft.taskProgress.progress}` : ""}。
          </p>
          <div className="resume-actions">
            <button onClick={handleResume} type="button">继续上次任务</button>
            <button className="secondary" onClick={() => { clearDraft(); setShowResume(false); setActiveStep(-1); setStatus(""); }} type="button">
              重新开始
            </button>
          </div>
        </div>
      )}

      <div className="new-case-layout">
      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          合同名称
          <input onChange={(event) => setTitle(event.target.value)} placeholder="输入合同名称" value={title} />
        </label>
        <label>
          我方立场
          <select defaultValue="party_a">
            <option value="party_a">甲方</option>
            <option value="party_b">乙方</option>
            <option value="other">其他</option>
          </select>
        </label>
        <label>
          审核重点
          <textarea onChange={(event) => setNote(event.target.value)} placeholder="例如：重点关注付款、违约责任和流程合规" value={note} />
        </label>
        <label>
          合同扫描件
          <input accept=".pdf,.png,.jpg,.jpeg,.txt,.md" onChange={(event) => setContract(event.target.files?.[0] ?? null)} type="file" />
          {contract && <span className="file-info">{contract.name} ({(contract.size / 1024 / 1024).toFixed(1)} MB)</span>}
        </label>
        <label>
          法审签报 PDF <span className="required-mark">必传</span>
          <input accept=".pdf,.txt,.md" onChange={(event) => setLegalReviewReport(event.target.files?.[0] ?? null)} required type="file" />
          <small className="field-hint">用于核对法审完成日期是否早于合同签订日期。</small>
          {legalReviewReport && <span className="file-info">{legalReviewReport.name}</span>}
        </label>
        <label>
          合同签批文件 PDF <span className="required-mark">必传</span>
          <input accept=".pdf,.txt,.md" onChange={(event) => setContractApproval(event.target.files?.[0] ?? null)} required type="file" />
          <small className="field-hint">用于核对合同签订日期是否早于最终审批通过日期。</small>
          {contractApproval && <span className="file-info">{contractApproval.name}</span>}
        </label>
        <label>
          事项签报 / 会议纪要 PDF <span className="optional-mark">可选</span>
          <input accept=".pdf,.txt,.md" onChange={(event) => setMatterMaterial(event.target.files?.[0] ?? null)} type="file" />
          <small className="field-hint">用于核对审批同意的事项与合同内容、范围是否一致。</small>
          {matterMaterial && <span className="file-info">{matterMaterial.name}</span>}
        </label>

        {isSubmitting && (
          <div className="upload-progress">
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: taskProgress ? `${taskProgress.progressPercent}%` : `${uploadProgress}%` }} />
            </div>
            <span>{taskProgress ? `${taskProgress.progressPercent}%` : `${uploadProgress}%`}</span>
          </div>
        )}

        <button disabled={isSubmitting} type="submit">
          {isSubmitting ? "处理中..." : "创建并上传"}
        </button>
        {status && <p className="status-line">{status}</p>}
      </form>
      <aside className="progress-panel">
        <h2>任务进度</h2>
        <ol className="progress-list">
          {PROGRESS_STEPS.map((step, index) => (
            <li className={index < activeStep ? "active" : index === activeStep ? "active current" : ""} key={step}>
              <span>{index + 1}</span>
              <div>
                {step}
                {index === activeStep && taskProgress?.progress && (
                  <small className="step-detail">{taskProgress.progress}</small>
                )}
              </div>
            </li>
          ))}
        </ol>
        {taskProgress && taskProgress.status === "running" && <div className="task-timer">审核进行中...</div>}
        {taskProgress?.error && <p className="task-error">{taskProgress.error}</p>}
      </aside>
      </div>
    </section>
  );
}
