type Details = Record<string, unknown>;
type Translation = string | ((details: Details) => string | null);

const text = (value: unknown): string => (typeof value === "string" ? value : "");
const named = (value: unknown): string => (typeof value === "string" ? `「${value}」` : "");
const limited = (details: Details, unit: string): string =>
  typeof details.limit === "number" ? `（${details.limit}${unit}まで）` : "";
const referenceKind = (details: Details): string => (details.kind === "tag" ? "タグ" : "ブランチ");

const trashConflicts: Record<string, string> = {
  commit_missing: "元の葉がありません",
  newer_note: "葉に新しいメモがあります",
  name_in_use: "同じ名前のブランチかタグがあります",
  preview_list_changed: "プレビューの一覧が変わっています。新しい操作から順に戻してください",
  bud_base_missing: "つぼみの元の葉がありません",
  changed_since: "削除した後に内容が変わっています",
  missing_reference: "戻すために必要な葉やブランチがありません",
  record_conflict: "戻す内容が今ある名前や順番と重なっています",
};

/** CLI error codes shown in the words of gui/README.md's 用語 section; any other code keeps the CLI's message. */
export const cliErrorTranslations: Record<string, Translation> = {
  not_initialized: "このフォルダはSproutプロジェクトではありません",
  already_initialized: "このフォルダはすでにSproutプロジェクトです",
  repository_locked: "別のSproutの操作が実行中です。終わってから再試行してください",
  // The other reasons name internal tables and keys, useful only as sent.
  unsupported_repository_format: (details) => (details.reason === "schema_version"
    ? `このプロジェクトの形式（${String(details.found_schema_version)}）は、今のSprout CLI（${String(details.supported_schema_version)}）では開けません`
    : null),

  path_outside_project: "プロジェクトの外にあるファイルは扱えません",
  sprout_metadata_path: "Sproutの管理フォルダ（.sprout）の中は扱えません",
  symlink_not_supported: "シンボリックリンクは追跡できません",
  path_not_found: "ファイルまたはフォルダが見つかりません",
  path_case_conflict: (details) => `大文字小文字などの表記だけが違うファイルと重なるため扱えません${details.conflicting_path ? `（${text(details.conflicting_path)}）` : ""}`,
  file_changed: "読み取り中にファイルが変更されました。もう一度お試しください",
  invalid_file_time: "保存されたファイルの更新日時が正しくありません",

  empty_message: "メッセージを入力してください",
  nothing_to_commit: "保存する変更がありません",
  commit_id_required: "葉を指定してください",
  unknown_commit: (details) => `葉${named(details.commit_id)}が見つかりません`,
  ambiguous_commit: (details) => `葉のID${named(details.commit_id)}に当てはまる葉が複数あります`,
  branch_has_no_commits: (details) => `ブランチ${named(details.name)}にはまだ葉がありません`,
  tagged_commit: (details) => `タグが付いた葉は削除できません。先にタグを削除してください${Array.isArray(details.tags) ? `（${details.tags.join("、")}）` : ""}`,
  delete_commit_failed: (details) => `葉を削除できませんでした。履歴は変更していません${details.reason ? `（${text(details.reason)}）` : ""}`,

  empty_label: "ラベルを入力してください",
  label_too_long: (details) => `ラベルが長すぎます${limited(details, "文字")}`,
  too_many_labels: (details) => `1つの葉に付けられるラベルの数を超えています${limited(details, "件")}`,
  note_too_long: (details) => `メモが長すぎます${limited(details, "文字")}`,

  unknown_branch: (details) => `ブランチ${named(details.name)}が見つかりません`,
  branch_exists: (details) => `ブランチ${named(details.name)}はすでにあります`,
  current_branch_delete: "現在のブランチは削除できません",
  unknown_tag: (details) => `タグ${named(details.name)}が見つかりません`,
  tag_exists: (details) => `タグ${named(details.name)}はすでにあります`,
  name_used_by_tag: (details) => `${named(details.name)}はタグの名前として使われています`,
  name_used_by_branch: (details) => `${named(details.name)}はブランチの名前として使われています`,
  invalid_reference_name: (details) => `${referenceKind(details)}の名前には空白を含めず、1文字以上入力してください`,
  reference_name_like_commit_id: (details) => `葉のIDと紛らわしいため、この${referenceKind(details)}の名前は使えません`,

  uncommitted_changes: "未保存の変更があります。先に保存するか、変更を破棄してください",
  untracked_conflict: "未追跡のファイルを上書きしてしまうため中止しました",
  restore_scope_conflict: "選択していないファイルにも影響するため、このファイルだけでは戻せません。葉へ移動してください",
  unsafe_restore_path: "安全に書き戻せないパスのため戻せません",
  file_identity_conflict: "同じ素材を指すファイルが重なるため戻せません",
  restore_recovery_conflict: "中断した復元の途中でファイルが変わっています。バックアップは残しています。対象を確認して再実行してください",
  restore_rollback_incomplete: "復元に失敗し、元の状態へ完全には戻せませんでした。もう一度操作すると復旧を試みます",

  unknown_bud: "つぼみが見つかりません",
  ambiguous_bud: "当てはまるつぼみが複数あります",
  invalid_bud_name: "つぼみの名前は改行なしの256文字までです",
  nothing_to_save: "つぼみへ移す未保存の変更がありません",

  thumbnail_not_found: "サムネイルの画像が見つかりません",
  thumbnail_not_file: "サムネイルにはファイルを指定してください",
  thumbnail_too_large: (details) => (typeof details.max_dimension === "number"
    ? `サムネイルの画像が大きすぎます（一辺${details.max_dimension}pxまで）`
    : "サムネイルの画像が大きすぎます（2 MiBまで）"),
  unsupported_thumbnail: "サムネイルにはPNG・JPEG・WebPの画像を指定してください",
  animated_thumbnail: "アニメーション画像はサムネイルに使えません",
  invalid_thumbnail: "サムネイルの画像を読み取れませんでした",
  no_thumbnail: "この葉にはサムネイルがありません",
  cover_not_tracked: "追跡中のファイルだけをサムネイル自動生成元にできます",
  cover_not_set: "サムネイル自動生成元が指定されていません",

  preview_file_not_found: "プレビューのファイルが見つかりません",
  preview_not_file: "プレビューにはファイルを指定してください",
  no_preview_files: "プレビューのファイルが指定されていません",
  preview_confirmation_required: "大きなファイルのため、プレビューへの追加には確認が必要です",
  unknown_preview: "この葉に該当するプレビューがありません",
  ambiguous_preview: "当てはまるプレビューが複数あります",
  invalid_preview_metadata: (details) => (details.field === "description"
    ? "プレビューの説明は20,000文字までです"
    : "プレビューの表示名は改行なしの256文字までです"),
  invalid_preview_order: "プレビューの一覧が変わっています。開き直してから並べ替えてください",

  path_not_in_commit: "この葉に含まれていないファイルです",
  export_into_metadata: "Sproutの管理フォルダ（.sprout）の中へは書き出せません",
  export_output_not_directory: "書き出し先がフォルダではありません",
  export_path_not_file: "書き出し先に同じ名前のフォルダなどがあるため書き出せません",
  export_output_exists: "書き出し先に同じ名前のファイルがあります。上書きはしません",
  export_would_change_tracked: "追跡中の作業ファイルを変更してしまうため書き出せません",
  export_unsafe_path: "リンクや書き出し先の外を指すパスには書き出せません",

  unknown_trash_item: "ゴミ箱の項目が見つかりません",
  invalid_trash_record: "復旧データが正しくないため復旧できません。項目はゴミ箱に残しています",
  trash_confirmation_required: "完全削除には確認が必要です",
  // An unknown reason has no Japanese wording yet, so the CLI's own message stays visible.
  trash_restore_conflict: (details) => {
    const reason = trashConflicts[text(details.reason_code)];
    return reason ? `復旧できません。${reason}。何も変更していません` : null;
  },
};

export function translateCliError(code: string, message: string, details: Details): string {
  const translation = Object.prototype.hasOwnProperty.call(cliErrorTranslations, code) ? cliErrorTranslations[code] : undefined;
  if (typeof translation === "function") return translation(details) ?? message;
  return translation ?? message;
}
