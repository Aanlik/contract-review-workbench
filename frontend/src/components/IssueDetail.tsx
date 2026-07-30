import { useEffect, useState } from "react";

import type { Issue, IssueUpdatePayload } from "../api/types";

type IssueDetailProps = {
  issue?: Issue;
  onSave: (issueId: number, payload: IssueUpdatePayload) => void;
  onReanalyze: () => void;
};

export function IssueDetail({ issue, onSave, onReanalyze }: IssueDetailProps) {
  const [draft, setDraft] = useState<IssueUpdatePayload>({});

  useEffect(() => {
    setDraft(
      issue
        ? {
            title: issue.title,
            riskLevel: issue.riskLevel as IssueUpdatePayload["riskLevel"],
            status: issue.status as IssueUpdatePayload["status"],
            description: issue.description ?? "",
            suggestion: issue.suggestion ?? "",
          }
        : {},
    );
  }, [issue]);

  if (!issue) {
    return <div className="empty-state">请选择一个问题查看详情。</div>;
  }

  return (
    <div className="issue-detail">
      <div className="detail-head">
        <input
          aria-label="问题标题"
          onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
          value={draft.title ?? ""}
        />
        <button onClick={onReanalyze} type="button">
          重新分析
        </button>
      </div>
      <label>
        风险等级
        <select
          onChange={(event) =>
            setDraft((current) => ({
              ...current,
              riskLevel: event.target.value as IssueUpdatePayload["riskLevel"],
            }))
          }
          value={draft.riskLevel ?? issue.riskLevel}
        >
          <option value="high">high</option>
          <option value="medium">medium</option>
          <option value="low">low</option>
          <option value="info">info</option>
        </select>
      </label>
      <label>
        状态
        <select
          onChange={(event) =>
            setDraft((current) => ({
              ...current,
              status: event.target.value as IssueUpdatePayload["status"],
            }))
          }
          value={draft.status ?? issue.status}
        >
          <option value="pending">pending</option>
          <option value="confirmed">confirmed</option>
          <option value="modified">modified</option>
          <option value="rejected">rejected</option>
          <option value="needs_review">needs_review</option>
        </select>
      </label>
      <label>
        问题说明
        <textarea
          onChange={(event) =>
            setDraft((current) => ({ ...current, description: event.target.value }))
          }
          value={draft.description ?? ""}
        />
      </label>
      <label>
        修改建议
        <textarea
          onChange={(event) => setDraft((current) => ({ ...current, suggestion: event.target.value }))}
          value={draft.suggestion ?? ""}
        />
      </label>
      <button onClick={() => onSave(issue.id, draft)} type="button">
        保存
      </button>
    </div>
  );
}
