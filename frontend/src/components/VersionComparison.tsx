import { useEffect, useState } from "react";

import { diffVersions, listCaseVersions } from "../api/client";
import type { ReviewVersion, VersionDiffItem } from "../api/types";
import { labelOf, riskLabels } from "../ui/labels";

type VersionComparisonProps = {
  caseId: number;
};

const riskColors: Record<string, string> = {
  high: "#dc3545",
  medium: "#ff9800",
  low: "#2196f3",
  info: "#6c757d",
};

const changeTypeColors: Record<string, string> = {
  added: "#28a745",
  removed: "#dc3545",
  modified: "#ff9800",
};

export function VersionComparison({ caseId }: VersionComparisonProps) {
  const [versions, setVersions] = useState<ReviewVersion[]>([]);
  const [versionA, setVersionA] = useState<number | null>(null);
  const [versionB, setVersionB] = useState<number | null>(null);
  const [changes, setChanges] = useState<VersionDiffItem[]>([]);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listCaseVersions(caseId).then((v) => {
      setVersions(v);
      if (v.length >= 2) {
        setVersionA(v[1].versionNumber);
        setVersionB(v[0].versionNumber);
      } else if (v.length === 1) {
        setVersionA(v[0].versionNumber);
        setVersionB(v[0].versionNumber);
      }
    });
  }, [caseId]);

  async function runDiff() {
    if (versionA === null || versionB === null) return;
    setLoading(true);
    try {
      const result = await diffVersions(caseId, versionA, versionB);
      setChanges(result.changes);
      setSummary(result.summary);
    } catch {
      setChanges([]);
      setSummary("对比失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (versionA !== null && versionB !== null && versionA !== versionB) {
      runDiff();
    }
  }, [versionA, versionB]);

  return (
    <div className="version-comparison">
      <h3>版本对比</h3>
      <div className="version-selectors">
        <label>
          基准版本
          <select
            onChange={(e) => setVersionA(Number(e.target.value))}
            value={versionA ?? ""}
          >
            {versions.map((v) => (
              <option key={v.versionNumber} value={v.versionNumber}>
                V{v.versionNumber} ({v.trigger})
              </option>
            ))}
          </select>
        </label>
        <span className="arrow">→</span>
        <label>
          目标版本
          <select
            onChange={(e) => setVersionB(Number(e.target.value))}
            value={versionB ?? ""}
          >
            {versions.map((v) => (
              <option key={v.versionNumber} value={v.versionNumber}>
                V{v.versionNumber} ({v.trigger})
              </option>
            ))}
          </select>
        </label>
        <button disabled={loading} onClick={runDiff} type="button">
          {loading ? "对比中..." : "对比"}
        </button>
      </div>

      {summary && <p className="diff-summary">{summary}</p>}

      {changes.length > 0 && (
        <div className="diff-list">
          {changes.map((change, i) => (
            <div
              className="diff-item"
              key={`${change.issueId}-${i}`}
              style={{ borderLeft: `4px solid ${changeTypeColors[change.changeType] ?? "#ccc"}` }}
            >
              <div className="diff-header">
                <span
                  className="change-badge"
                  style={{ background: changeTypeColors[change.changeType] ?? "#ccc" }}
                >
                    {change.changeType === "added" ? "新增" : change.changeType === "removed" ? "移除" : "变更"}
                </span>
                <strong>{change.title}</strong>
                <span
                  className="risk-badge"
                  style={{ color: riskColors[change.riskLevel] ?? "#888" }}
                >
                    {labelOf(riskLabels, change.riskLevel)}
                    {change.oldRiskLevel && change.oldRiskLevel !== change.riskLevel && (
                      <span className="old-risk">（原：{labelOf(riskLabels, change.oldRiskLevel)}）</span>
                  )}
                </span>
              </div>
              <p className="diff-description">{change.description}</p>
            </div>
          ))}
        </div>
      )}

      {versionA !== null && versionB !== null && versionA === versionB && (
        <p className="empty-state">请选择两个不同的版本进行对比。</p>
      )}

      {versionA !== null && versionB !== null && versionA !== versionB && changes.length === 0 && !loading && (
        <p className="empty-state">两个版本之间没有差异。</p>
      )}
    </div>
  );
}
