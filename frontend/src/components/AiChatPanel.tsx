type AiChatPanelProps = {
  scopeLabel: string;
};

export function AiChatPanel({ scopeLabel }: AiChatPanelProps) {
  return (
    <div className="ai-chat">
      <h2>AI 互动</h2>
      <p>{scopeLabel}</p>
      <div className="chat-history">对话会按任务和问题持久化保存。</div>
      <textarea placeholder="例如：站在甲方角度重新分析这个条款" />
      <div className="chat-actions">
        <button type="button">发送</button>
        <button type="button">应用为建议</button>
        <button type="button">应用为新问题</button>
      </div>
    </div>
  );
}
