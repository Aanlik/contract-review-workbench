import type { Issue } from "../api/types";

type IssueListProps = {
  issues: Issue[];
  filters: Record<string, string>;
  selectedIssueId?: number;
  onFilterChange: (filters: Record<string, string>) => void;
  onSelect: (issueId: number) => void;
};

const tabs = [
  ["", "全部"],
  ["contract_risk", "合同风险"],
  ["process_audit", "流程审计"],
  ["manual_mark", "人工标记"],
];
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

export function IssueList({ filters, issues, selectedIssueId, onFilterChange, onSelect }: IssueListProps) {
  const filteredIssues = issues.filter((issue) => {
    if (filters.issueType && issue.issueType !== filters.issueType) return false;
    if (filters.riskLevel && issue.riskLevel !== filters.riskLevel) return false;
    if (filters.status && issue.status !== filters.status) return false;
    return true;
  });

  function updateFilter(key: string, value: string) {
    onFilterChange({ ...filters, [key]: value });
  }

  return (
    <div className="issue-list">
      <div className="toolbar-tabs">
        {tabs.map(([value, label]) => (
          <button
            className={(filters.issueType ?? "") === value ? "active" : ""}
            key={value || "all"}
            onClick={() => updateFilter("issueType", value)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>
      <div className="filter-row">
        <select
          aria-label="风险等级"
          onChange={(event) => updateFilter("riskLevel", event.target.value)}
          value={filters.riskLevel ?? ""}
        >
          {risks.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          aria-label="问题状态"
          onChange={(event) => updateFilter("status", event.target.value)}
          value={filters.status ?? ""}
        >
          {statuses.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div className="issue-items">
        {filteredIssues.map((issue) => (
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
        {!filteredIssues.length && <p className="empty-state">当前筛选下没有问题。</p>}
      </div>
    </div>
  );
}
