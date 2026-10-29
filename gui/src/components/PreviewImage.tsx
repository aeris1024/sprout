import { useEffect, useState } from "react";
import { normalizeCliError, runSprout, type CommitAttachment } from "../lib/sprout";

type ImageReply = { data_url: string; width: number; height: number; display_width: number; display_height: number };
export default function PreviewImage({ projectDir, program, attachment, onClose }: {
  projectDir: string; program: string; attachment: CommitAttachment; onClose: () => void;
}) {
  const [image, setImage] = useState<ImageReply | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setImage(null);
    setError("");
    void runSprout<ImageReply>(projectDir, ["preview", "image", attachment.commit_id, attachment.id], program)
      .then((reply) => { if (active) setImage(reply); })
      .catch((cause) => { if (active) setError(normalizeCliError(cause).message); });
    return () => { active = false; };
  }, [projectDir, program, attachment.commit_id, attachment.id, attachment.object_hash, attempt]);
  return <section className="preview-image" aria-label="画像プレビュー">
    <div className="panel-heading"><h4>{attachment.original_name}</h4><button className="icon-button" onClick={onClose} aria-label="画像表示を閉じる">×</button></div>
    {error ? <div role="alert"><p>{error}</p><p className="panel-copy">一覧の「取り出す」で原本を保存できます。</p><button className="button secondary" onClick={() => setAttempt((value) => value + 1)}>画像を再読み込み</button></div>
      : image ? <><img src={image.data_url} alt={attachment.original_name} onError={() => { setImage(null); setError("画像を表示できませんでした。取り出して確認してください。"); }} /><p className="panel-copy">{image.width} × {image.height} px{image.width !== image.display_width || image.height !== image.display_height ? "（表示用に縮小）" : ""}</p></>
      : <p role="status">画像を読み込み中…</p>}
  </section>;
}
