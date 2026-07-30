import type { Issue } from "../api/types";

type IssueListProps = {
  issues: Issue[];
  selectedIssueId?: number;
  onSelect: (issueId: number) => void;
};

const tabs = ["全部", "合同风险", "流程审计", "人工标记"];
const risks = [
  ["", "全部等级"],
  ["high", "高风险"],
  ["medium", "中风险"],
  ["low", "低风险"],
  ["info", "提示"],
];
const statuses = [
  ["", "全部状态"],
  ["pending", "待处理"],
  ["confirmed", "已确认"],
  ["modified", "已修改"],
  ["rejected", "不采纳"],
  ["needs_review", "待复核"],
];

export function IssueList({ issues, selectedIssueId, onSelect }: IssueListProps) {
  return (
    <div className="issue-list">
      <div className="toolbar-tabs">
        {tabs.map((tab) => (
          <button key={tab} type="button">
            {tab}
          </button>
        ))}
      </div>
      <div className="filter-row">
        <select aria-label="风险等级">
          {risks.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select aria-label="问题状态">
          {statuses.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div className="issue-items">
        {issues.map((issue) => (
          <button
            className={issue.id === selectedIssueId ? "issue-item selected" : "issue-item"}
            key={issue.id}
            onClick={() => onSelect(issue.id)}
            type="button"
          >
            <strong>{issue.title}</strong>
            <span>{issue.riskLevel}</span>
            <span>{issue.source}</span>
            <span>{issue.status}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
