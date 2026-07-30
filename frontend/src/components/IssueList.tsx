import { useState } from "react";

import type { Issue } from "../api/types";

type IssueListProps = {
  issues: Issue[];
  filters: Record<string, string>;
  selectedIssueId?: number;
  onFilterChange: (filters: Record<string, string>) => void;
  onSelect: (issueId: number) => void;
  onBatchUpdate: (issueIds: number[], updates: { status?: string; riskLevel?: string }) => void;
  onBatchDelete: (issueIds: number[]) => void;
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

const riskColors: Record<string, string> = {
  high: "#dc3545",
  medium: "#ff9800",
  low: "#2196f3",
  info: "#6c757d",
};

export function IssueList({
  filters,
  issues,
  selectedIssueId,
  onBatchDelete,
  onBatchUpdate,
  onFilterChange,
  onSelect,
}: IssueListProps) {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [batchMode, setBatchMode] = useState(false);

  const filteredIssues = issues.filter((issue) => {
    if (filters.issueType && issue.issueType !== filters.issueType) return false;
    if (filters.riskLevel && issue.riskLevel !== filters.riskLevel) return false;
    if (filters.status && issue.status !== filters.status) return false;
    return true;
  });

  function updateFilter(key: string, value: string) {
    onFilterChange({ ...filters, [key]: value });
  }

  function toggleSelect(issueId: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(issueId)) next.delete(issueId);
      else next.add(issueId);
      return next;
    });
  }

  function selectAll() {
    if (selectedIds.size === filteredIssues.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredIssues.map((i) => i.id)));
    }
  }

  function handleBatchStatus(status: string) {
    if (selectedIds.size === 0) return;
    onBatchUpdate(Array.from(selectedIds), { status });
    setSelectedIds(new Set());
    setBatchMode(false);
  }

  function handleBatchDelete() {
    if (selectedIds.size === 0) return;
    onBatchDelete(Array.from(selectedIds));
    setSelectedIds(new Set());
    setBatchMode(false);
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
        <button
          className={batchMode ? "batch-toggle active" : "batch-toggle"}
          onClick={() => {
            setBatchMode(!batchMode);
            if (batchMode) setSelectedIds(new Set());
          }}
          type="button"
        >
          {batchMode ? "取消批量" : "批量操作"}
        </button>
      </div>

      {batchMode && (
        <div className="batch-toolbar">
          <button onClick={selectAll} type="button">
            {selectedIds.size === filteredIssues.length ? "取消全选" : "全选"}
          </button>
          <span className="batch-count">已选 {selectedIds.size} 项</span>
          <button disabled={!selectedIds.size} onClick={() => handleBatchStatus("confirmed")} type="button">
            批量确认
          </button>
          <button disabled={!selectedIds.size} onClick={() => handleBatchStatus("rejected")} type="button">
            批量不采纳
          </button>
          <button disabled={!selectedIds.size} onClick={() => handleBatchStatus("needs_review")} type="button">
            批量待复核
          </button>
          <button className="danger" disabled={!selectedIds.size} onClick={handleBatchDelete} type="button">
            批量删除
          </button>
        </div>
      )}

      <div className="issue-items">
        {filteredIssues.map((issue) => (
          <div
            className={issue.id === selectedIssueId ? "issue-item selected" : "issue-item"}
            key={issue.id}
          >
            {batchMode && (
              <input
                checked={selectedIds.has(issue.id)}
                onChange={() => toggleSelect(issue.id)}
                type="checkbox"
              />
            )}
            <button
              className="issue-item-btn"
              onClick={() => onSelect(issue.id)}
              type="button"
            >
              <strong>{issue.title}</strong>
              <span className="risk-tag" style={{ color: riskColors[issue.riskLevel] ?? "#888" }}>
                {issue.riskLevel}
              </span>
              <span className="source-tag">{issue.source}</span>
              <span className="status-tag">{issue.status}</span>
            </button>
          </div>
        ))}
        {!filteredIssues.length && <p className="empty-state">当前筛选下没有问题。</p>}
      </div>
    </div>
  );
}
