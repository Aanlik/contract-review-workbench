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
    setStatus("正在创建审核任务...");
    const reviewCase = await createCase({ title, note });
    await uploadCaseFile(reviewCase.id, "contract", contract);
    if (signReport) await uploadCaseFile(reviewCase.id, "sign_report", signReport);
    if (meetingMinutes) await uploadCaseFile(reviewCase.id, "meeting_minutes", meetingMinutes);
    setStatus("正在执行首次审核...");
    await reanalyzeCase(reviewCase.id, note || "首次审核");
    setStatus("审核任务已创建。");
    onCreated(reviewCase.id);
  }

  return (
    <section>
      <header className="page-header">
        <h1>新建审核</h1>
      </header>
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
    </section>
  );
}
