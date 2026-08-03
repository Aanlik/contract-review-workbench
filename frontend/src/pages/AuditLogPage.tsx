import { useEffect, useState } from "react";
import { getAuditLogs } from "../api/client";

interface AuditEntry {
  id: number;
  action: string;
  entityType: string;
  entityId: number | null;
  user: string;
  details: Record<string, any> | null;
  createdAt: string;
}

const ACTION_LABELS: Record<string, string> = {
  create: "创建",
  update: "更新",
  delete: "删除",
  create_manual_issue: "人工标记",
  batch_update: "批量更新",
  batch_delete: "批量删除",
  apply_ai_message: "应用智能建议",
};

const ACTION_CLASSES: Record<string, string> = {
  create: "audit-action-create",
  update: "audit-action-update",
  delete: "audit-action-delete",
  create_manual_issue: "audit-action-update",
  batch_update: "audit-action-update",
  batch_delete: "audit-action-delete",
  apply_ai_message: "audit-action-create",
};

export function AuditLogPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [entityType, setEntityType] = useState<string>("");
  const [loading, setLoading] = useState(true);

  async function fetchLogs() {
    setLoading(true);
    try {
      const data = await getAuditLogs({
        entityType: entityType || undefined,
        limit: 200,
      });
      setLogs(data);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchLogs();
  }, [entityType]);

  return (
    <section className="audit-page">
      <header className="page-header">
        <div>
          <p className="section-kicker">操作记录</p>
          <h1>审计日志</h1>
        </div>
        <div className="page-actions">
          <select value={entityType} onChange={(e) => setEntityType(e.target.value)}>
            <option value="">全部类型</option>
            <option value="case">审核案件</option>
            <option value="issue">问题</option>
          </select>
          <button className="secondary" onClick={fetchLogs} type="button">刷新</button>
        </div>
      </header>

      {loading ? (
        <p className="empty-state">加载中...</p>
      ) : logs.length === 0 ? (
        <p className="empty-state">暂无审计记录。</p>
      ) : (
        <div className="table-wrap">
          <table className="audit-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>操作</th>
                <th>对象类型</th>
                <th>对象ID</th>
                <th>用户</th>
                <th>详情</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{log.createdAt ? new Date(log.createdAt).toLocaleString("zh-CN") : "-"}</td>
                  <td>
                    <span className={`audit-action ${ACTION_CLASSES[log.action] || ""}`}>
                      {ACTION_LABELS[log.action] || log.action}
                    </span>
                  </td>
                  <td>{log.entityType === "case" ? "案件" : log.entityType === "issue" ? "问题" : log.entityType}</td>
                  <td>{log.entityId ?? "-"}</td>
                  <td>{log.user}</td>
                  <td style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {log.details ? JSON.stringify(log.details).slice(0, 120) : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
