import { useEffect } from "react";
import type { SproutCliError } from "../lib/sprout";

export type NoticeData = SproutCliError & { kind: "error" | "success" | "warning" };

export default function Notice({ notice, onClose, onRetry }: { notice: NoticeData | null; onClose: () => void; onRetry?: () => void }) {
  useEffect(() => {
    if (notice?.kind !== "success") return;
    const timer = setTimeout(onClose, 5000);
    return () => clearTimeout(timer);
  }, [notice, onClose]);

  return <div className="notice-region">
    {notice && <div className={`notice ${notice.kind}`} role={notice.kind === "success" ? "status" : "alert"} aria-atomic="true">
      <div><strong>{notice.kind === "error" ? "操作を完了できませんでした" : notice.kind === "warning" ? "確認してください" : "完了"}</strong>
        <p>{notice.message}</p>
        {typeof notice.details.path === "string" && <p className="notice-path">対象: {notice.details.path}</p>}
        {notice.kind !== "success" && <details><summary>エラーの詳細</summary><p>code: {notice.code}</p>{notice.originalMessage && notice.originalMessage !== notice.message && <p>{notice.originalMessage}</p>}</details>}
      </div>
      <div className="notice-actions">{notice.code === "repository_locked" && onRetry && <button onClick={onRetry}>再試行</button>}
        <button aria-label="通知を閉じる" onClick={onClose}>×</button>
      </div>
    </div>}
  </div>;
}
