import { useState } from "react";

import type { AiMessage } from "../api/types";

const roleLabels: Record<string, string> = {
  user: "我方",
  assistant: "智能助手",
  system: "系统",
};

type AiChatPanelProps = {
  scopeLabel: string;
  messages: AiMessage[];
  onSend: (message: string) => void;
  onApplyAsSuggestion: (messageId: number) => void;
  onApplyAsNewIssue: (messageId: number) => void;
};

export function AiChatPanel({
  scopeLabel,
  messages,
  onApplyAsNewIssue,
  onApplyAsSuggestion,
  onSend,
}: AiChatPanelProps) {
  const [draft, setDraft] = useState("");
  const latestAssistant = [...messages].reverse().find((message) => message.role === "assistant");

  function send() {
    if (!draft.trim()) return;
    onSend(draft.trim());
    setDraft("");
  }

  return (
    <div className="ai-chat">
      <h2>智能互动</h2>
      <p>{scopeLabel}</p>
      <div className="chat-history">
        {messages.length ? (
          messages.map((message) => (
            <div className={`chat-message ${message.role}`} key={message.id}>
              <b>{roleLabels[message.role] ?? "消息"}</b>
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
        <button
          disabled={!latestAssistant}
          onClick={() => latestAssistant && onApplyAsSuggestion(latestAssistant.id)}
          type="button"
        >
          应用为建议
        </button>
        <button
          disabled={!latestAssistant}
          onClick={() => latestAssistant && onApplyAsNewIssue(latestAssistant.id)}
          type="button"
        >
          应用为新问题
        </button>
      </div>
    </div>
  );
}
