import type { Issue } from "../api/types";

type IssueDetailProps = {
  issue?: Issue;
};

export function IssueDetail({ issue }: IssueDetailProps) {
  if (!issue) {
    return <div className="empty-state">请选择一个问题查看详情。</div>;
  }

  return (
    <div className="issue-detail">
      <div className="detail-head">
        <h2>{issue.title}</h2>
        <button type="button">重新分析</button>
      </div>
      <label>
        风险等级
        <select defaultValue={issue.riskLevel}>
          <option value="high">high</option>
          <option value="medium">medium</option>
          <option value="low">low</option>
          <option value="info">info</option>
        </select>
      </label>
      <label>
        状态
        <select defaultValue={issue.status}>
          <option value="pending">pending</option>
          <option value="confirmed">confirmed</option>
          <option value="modified">modified</option>
          <option value="rejected">rejected</option>
          <option value="needs_review">needs_review</option>
        </select>
      </label>
      <label>
        问题说明
        <textarea defaultValue={issue.description ?? ""} />
      </label>
      <label>
        修改建议
        <textarea defaultValue={issue.suggestion ?? ""} />
      </label>
      <button type="button">保存</button>
    </div>
  );
}
