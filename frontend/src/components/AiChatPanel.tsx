import { useState } from "react";

import type { AiMessage } from "../api/types";

type AiChatPanelProps = {
  scopeLabel: string;
  messages: AiMessage[];
  onSend: (message: string) => void;
};

export function AiChatPanel({ scopeLabel, messages, onSend }: AiChatPanelProps) {
  const [draft, setDraft] = useState("");

  function send() {
    if (!draft.trim()) return;
    onSend(draft.trim());
    setDraft("");
  }

  return (
    <div className="ai-chat">
      <h2>AI 互动</h2>
      <p>{scopeLabel}</p>
      <div className="chat-history">
        {messages.length ? (
          messages.map((message) => (
            <div className={`chat-message ${message.role}`} key={message.id}>
              <b>{message.role}</b>
              <p>{message.content}</p>
            </div>
          ))
        ) : (
          <span>对话会按任务和问题持久化保存。</span>
        )}
      </div>
      <textarea
        onChange={(event) => setDraft(event.target.value)}
        placeholder="例如：站在甲方角度重新分析这个条款"
        value={draft}
      />
      <div className="chat-actions">
        <button onClick={send} type="button">
          发送
        </button>
        <button type="button">应用为建议</button>
        <button type="button">应用为新问题</button>
      </div>
    </div>
  );
}
