import { formatBytes, type DoctorReport, type GcResult, type RepositoryStats } from "../lib/sprout";

const issueLabels: Record<string, string> = {
  missing_object: "内容の欠落",
  corrupt_object: "内容の破損",
  object_size_mismatch: "サイズの不一致",
  unsupported_object_encoding: "非対応の保存形式",
  unregistered_object: "未登録の内容",
  orphan_temp: "残った一時ファイル",
  active_operation: "中断中の操作",
  missing_current_commit: "現在位置の欠落",
  missing_bud_base: "つぼみの起点の欠落",
  invalid_file_time: "不正な更新日時",
  invalid_trash_record: "不正な復旧記録",
  missing_file_identity: "素材IDの欠落",
  invalid_sequence: "不正な連番",
  invalid_path_key: "不正なパス識別子",
  path_conflict: "衝突するパス",
};

interface MaintenancePanelProps {
  stats: RepositoryStats | null;
  gcResult: GcResult | null;
  doctor: DoctorReport | null;
  busy: boolean;
  onCollect: () => void;
  onCheck: () => void;
  onClose: () => void;
}

export default function MaintenancePanel({ stats, gcResult, doctor, busy, onCollect, onCheck, onClose }: MaintenancePanelProps) {
  return (
    <section className="panel-section" aria-label="保守">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">MAINTENANCE</p>
          <h3>保守</h3>
        </div>
        <button className="icon-button" onClick={onClose} aria-label="保守を閉じる">×</button>
      </div>

      <section className="annotation-section" aria-label="容量と件数">
        <h4>容量と件数</h4>
        {stats ? (
          <dl className="detail-list">
            <div><dt>コミット</dt><dd>{stats.commits.toLocaleString()}件</dd></div>
            <div><dt>ブランチ</dt><dd>{stats.branches.toLocaleString()}件</dd></div>
            <div><dt>追跡パス</dt><dd>{stats.tracked_paths.toLocaleString()}件</dd></div>
            <div><dt>つぼみ</dt><dd>{stats.buds.toLocaleString()}件</dd></div>
            <div><dt>オブジェクト</dt><dd>{stats.objects.toLocaleString()}個</dd></div>
            <div><dt>論理容量</dt><dd>{formatBytes(stats.logical_bytes)}</dd></div>
            <div><dt>実容量</dt><dd>{formatBytes(stats.objects_bytes)}</dd></div>
            <div><dt>重複排除の節約</dt><dd>{formatBytes(stats.dedup_saved_bytes)}</dd></div>
          </dl>
        ) : <p className="muted">読み込み中…</p>}
      </section>

      <section className="annotation-section" aria-label="容量の回収">
        <h4>容量の回収</h4>
        <p className="panel-copy">どこからも参照されない内容と一時ファイルを削除します。ゴミ箱に保持中のデータは回収しません。回収するには先にゴミ箱で完全削除してください。</p>
        <button className="button secondary" onClick={onCollect} disabled={busy}>回収できる容量を確認</button>
        {gcResult && <p role="status" className="panel-copy">{`オブジェクト ${gcResult.removed_objects.toLocaleString()}個、一時ファイル ${gcResult.removed_temps.toLocaleString()}個を削除し、${formatBytes(gcResult.freed_bytes)}を回収しました。`}</p>}
      </section>

      <section className="annotation-section" aria-label="整合性検査">
        <h4>整合性検査</h4>
        <p className="panel-copy">保存した内容を読み直して確認します。ファイルや履歴は変更しません。</p>
        <button className="button secondary" onClick={onCheck} disabled={busy}>検査する</button>
        {doctor && (doctor.ok ? (
          <p role="status" className="panel-copy">{`問題はありません（${doctor.checked_objects.toLocaleString()}個を検査）`}</p>
        ) : (
          <div role="status">
            <p className="panel-copy">{`${doctor.issues.length.toLocaleString()}件の問題が見つかりました（${doctor.checked_objects.toLocaleString()}個を検査）`}</p>
            <ul className="attachment-list" aria-label="検査で見つかった問題">
              {doctor.issues.map((issue, index) => <li key={`${issue.kind}:${issue.detail}:${index}`}>{`${issueLabels[issue.kind] ?? issue.kind}: ${issue.detail}`}</li>)}
            </ul>
          </div>
        ))}
      </section>
    </section>
  );
}
