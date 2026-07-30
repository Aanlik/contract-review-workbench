import { useEffect, useRef, type ReactNode } from "react";

type ModalProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: number;
};

export function Modal({ children, onClose, open, title, width = 420 }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="modal-overlay"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      ref={overlayRef}
    >
      <div className="modal-content" style={{ maxWidth: width }}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="modal-close" onClick={onClose} type="button">×</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

type ConfirmDialogProps = {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
};

export function ConfirmDialog({ danger, message, onClose, onConfirm, open, title, confirmLabel = "确认" }: ConfirmDialogProps) {
  return (
    <Modal onClose={onClose} open={open} title={title}>
      <p className="modal-message">{message}</p>
      <div className="modal-actions">
        <button className="secondary" onClick={onClose} type="button">取消</button>
        <button className={danger ? "danger" : ""} onClick={() => { onConfirm(); onClose(); }} type="button">
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}

type PromptDialogProps = {
  open: boolean;
  onClose: () => void;
  onSubmit: (value: string) => void;
  title: string;
  label: string;
  defaultValue?: string;
  placeholder?: string;
};

export function PromptDialog({ defaultValue, label, onClose, onSubmit, open, placeholder, title }: PromptDialogProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.value = defaultValue ?? "";
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [open, defaultValue]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const val = inputRef.current?.value ?? "";
    if (val.trim()) onSubmit(val.trim());
    onClose();
  }

  return (
    <Modal onClose={onClose} open={open} title={title}>
      <form onSubmit={handleSubmit}>
        <label className="modal-field">
          {label}
          <input ref={inputRef} placeholder={placeholder} />
        </label>
        <div className="modal-actions">
          <button className="secondary" onClick={onClose} type="button">取消</button>
          <button type="submit">确定</button>
        </div>
      </form>
    </Modal>
  );
}

type RenameDialogProps = {
  open: boolean;
  onClose: () => void;
  onSubmit: (title: string, note: string) => void;
  defaultTitle?: string;
  defaultNote?: string;
};

export function RenameDialog({ defaultNote, defaultTitle, onClose, onSubmit, open }: RenameDialogProps) {
  const titleRef = useRef<HTMLInputElement>(null);
  const noteRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open && titleRef.current) {
      titleRef.current.value = defaultTitle ?? "";
      noteRef.current!.value = defaultNote ?? "";
      titleRef.current.focus();
    }
  }, [open, defaultTitle, defaultNote]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const t = titleRef.current?.value ?? "";
    const n = noteRef.current?.value ?? "";
    if (t.trim()) onSubmit(t.trim(), n.trim());
    onClose();
  }

  return (
    <Modal onClose={onClose} open={open} title="重命名审核记录">
      <form onSubmit={handleSubmit}>
        <label className="modal-field">
          合同名称
          <input ref={titleRef} placeholder="输入合同名称" />
        </label>
        <label className="modal-field">
          备注
          <input ref={noteRef} placeholder="输入备注" />
        </label>
        <div className="modal-actions">
          <button className="secondary" onClick={onClose} type="button">取消</button>
          <button type="submit">保存</button>
        </div>
      </form>
    </Modal>
  );
}

type ExportDialogProps = {
  open: boolean;
  onClose: () => void;
  onExport: (scope: string, format: string) => void;
};

export function ExportDialog({ onClose, onExport, open }: ExportDialogProps) {
  const scopeRef = useRef<HTMLSelectElement>(null);
  const formatRef = useRef<HTMLSelectElement>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onExport(scopeRef.current?.value ?? "final", formatRef.current?.value ?? "markdown");
    onClose();
  }

  return (
    <Modal onClose={onClose} open={open} title="导出审核报告">
      <form onSubmit={handleSubmit}>
        <label className="modal-field">
          导出范围
          <select ref={scopeRef}>
            <option value="final">最终版（所有问题）</option>
            <option value="all">全部（含历史版本）</option>
            <option value="high_and_medium">高 + 中风险</option>
            <option value="confirmed">已确认问题</option>
          </select>
        </label>
        <label className="modal-field">
          导出格式
          <select ref={formatRef}>
            <option value="markdown">Markdown (.md)</option>
            <option value="docx">Word (.docx)</option>
            <option value="pdf">PDF / HTML (.html)</option>
          </select>
        </label>
        <div className="modal-actions">
          <button className="secondary" onClick={onClose} type="button">取消</button>
          <button type="submit">导出</button>
        </div>
      </form>
    </Modal>
  );
}
