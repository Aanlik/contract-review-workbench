import { useEffect, useState } from "react";

import type { Issue, IssueUpdatePayload } from "../api/types";
import { localizeUiText, riskLabels, statusLabels } from "../ui/labels";

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
            title: localizeUiText(issue.title),
            riskLevel: issue.riskLevel as IssueUpdatePayload["riskLevel"],
            status: issue.status as IssueUpdatePayload["status"],
            description: localizeUiText(issue.description ?? ""),
            suggestion: localizeUiText(issue.suggestion ?? ""),
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
          {Object.entries(riskLabels).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
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
          {Object.entries(statusLabels)
            .filter(([value]) => ["pending", "confirmed", "modified", "rejected", "needs_review"].includes(value))
            .map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
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
