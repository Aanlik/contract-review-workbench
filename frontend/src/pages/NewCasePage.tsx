import { FormEvent, useState } from "react";

import { createCase, reanalyzeCase, uploadCaseFile } from "../api/client";

type NewCasePageProps = {
  onCreated: (caseId: number) => void;
};

export function NewCasePage({ onCreated }: NewCasePageProps) {
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [contract, setContract] = useState<File | null>(null);
  const [signReport, setSignReport] = useState<File | null>(null);
  const [meetingMinutes, setMeetingMinutes] = useState<File | null>(null);
  const [status, setStatus] = useState("");
  const [activeStep, setActiveStep] = useState(0);

  const progressSteps = [
    "文件上传",
    "PDF 解析",
    "OCR 识别",
    "合同法律风险审查",
    "流程合规审计",
    "生成结果",
  ];

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) {
      setStatus("请先填写合同名称。");
      return;
    }
    if (!contract) {
      setStatus("请上传合同扫描件。");
      return;
    }
    try {
      setActiveStep(0);
      setStatus("正在创建审核任务...");
      const reviewCase = await createCase({ title, note });
      await uploadCaseFile(reviewCase.id, "contract", contract);
      if (signReport) await uploadCaseFile(reviewCase.id, "sign_report", signReport);
      if (meetingMinutes) await uploadCaseFile(reviewCase.id, "meeting_minutes", meetingMinutes);
      setActiveStep(2);
      setStatus("正在读取材料并准备 OCR/文本抽取...");
      setActiveStep(3);
      setStatus("正在执行首次 AI 审查和流程合规审计...");
      await reanalyzeCase(reviewCase.id, note || "首次审核");
      setActiveStep(5);
      setStatus("审核任务已创建。");
      onCreated(reviewCase.id);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "任务创建失败，请重试。");
    }
  }

  return (
    <section className="new-case-page">
      <header className="page-header">
        <div>
          <p className="section-kicker">Upload & Analyze</p>
          <h1>新建审核</h1>
        </div>
      </header>
      <div className="new-case-layout">
      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          合同名称
          <input
            onChange={(event) => setTitle(event.target.value)}
            placeholder="输入合同名称"
            value={title}
          />
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
          <textarea
            onChange={(event) => setNote(event.target.value)}
            placeholder="例如：重点关注付款、违约责任和流程合规"
            value={note}
          />
        </label>
        <label>
          合同扫描件
          <input
            accept=".pdf,.png,.jpg,.jpeg,.txt,.md"
            onChange={(event) => setContract(event.target.files?.[0] ?? null)}
            type="file"
          />
        </label>
        <label>
          OA 签报 PDF
          <input
            accept=".pdf,.txt,.md"
            onChange={(event) => setSignReport(event.target.files?.[0] ?? null)}
            type="file"
          />
        </label>
        <label>
          会议纪要 PDF
          <input
            accept=".pdf,.txt,.md"
            onChange={(event) => setMeetingMinutes(event.target.files?.[0] ?? null)}
            type="file"
          />
        </label>
        <button type="submit">创建并上传</button>
        {status && <p className="status-line">{status}</p>}
      </form>
      <aside className="progress-panel">
        <h2>任务进度</h2>
        <ol className="progress-list">
          {progressSteps.map((step, index) => (
            <li className={index <= activeStep ? "active" : ""} key={step}>
              <span>{index + 1}</span>
              {step}
            </li>
          ))}
        </ol>
      </aside>
      </div>
    </section>
  );
}
