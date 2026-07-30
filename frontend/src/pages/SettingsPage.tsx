import { FormEvent, useEffect, useState } from "react";

import { getAiSettings, saveAiSettings } from "../api/client";
import type { AiSettings } from "../api/types";

const emptySettings: AiSettings = {
  baseUrl: "",
  apiKey: "",
  model: "",
  temperature: 0.2,
  timeoutSeconds: 60,
};

export function SettingsPage() {
  const [settings, setSettings] = useState<AiSettings>(emptySettings);
  const [status, setStatus] = useState("");

  useEffect(() => {
    getAiSettings()
      .then((value) => {
        if (value) setSettings(value);
      })
      .catch(() => setStatus("尚未读取到 AI 配置。"));
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await saveAiSettings(settings);
    setStatus("AI 配置已保存。");
  }

  return (
    <section>
      <header className="page-header">
        <h1>设置</h1>
      </header>
      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          AI Base URL
          <input
            onChange={(event) => setSettings((current) => ({ ...current, baseUrl: event.target.value }))}
            placeholder="https://api.example.com/v1"
            value={settings.baseUrl}
          />
        </label>
        <label>
          模型名
          <input
            onChange={(event) => setSettings((current) => ({ ...current, model: event.target.value }))}
            placeholder="model-name"
            value={settings.model}
          />
        </label>
        <label>
          API Key
          <input
            onChange={(event) => setSettings((current) => ({ ...current, apiKey: event.target.value }))}
            placeholder="sk-..."
            type="password"
            value={settings.apiKey}
          />
        </label>
        <label>
          温度
          <input
            max="2"
            min="0"
            onChange={(event) =>
              setSettings((current) => ({ ...current, temperature: Number(event.target.value) }))
            }
            step="0.1"
            type="number"
            value={settings.temperature}
          />
        </label>
        <label>
          超时秒数
          <input
            min="1"
            onChange={(event) =>
              setSettings((current) => ({ ...current, timeoutSeconds: Number(event.target.value) }))
            }
            type="number"
            value={settings.timeoutSeconds}
          />
        </label>
        <button type="submit">保存配置</button>
        {status && <p className="status-line">{status}</p>}
      </form>
    </section>
  );
}
