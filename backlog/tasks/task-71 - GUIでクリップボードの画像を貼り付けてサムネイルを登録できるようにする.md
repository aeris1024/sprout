---
id: TASK-71
title: GUIでクリップボードの画像を貼り付けてサムネイルを登録できるようにする
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-29T14:27:00Z'
updated_date: '2026-10-29T14:33:00Z'
labels: []
dependencies: []
references:
  - gui/src/App.tsx
  - gui/src-tauri/src/lib.rs
priority: low
type: feature
ordinal: 71000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUIでサムネイルを登録する際、ファイル選択に加えてCtrl+Vでクリップボードの画像を貼り付けて登録できるようにする。保存パネル（新規コミット時）とコミット詳細（既存コミットへの登録・変更）の両方を対象とする。previewへの貼り付けはGUIのpreview管理画面と合わせて後で扱う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 保存パネルでCtrl+Vした画像がコミット時のサムネイルとして登録される
- [x] #2 コミット詳細を表示中にCtrl+Vした画像がそのコミットのサムネイルとして登録・置き換えされる
- [x] #3 メッセージ欄へのテキスト貼り付けは従来どおり動作し、画像以外の貼り付けでサムネイルが変わらない
- [x] #4 PNG・JPEG・WebP以外や2 MiB超の画像は登録せず警告を表示する
- [x] #5 貼り付けで作成した一時ファイルは使用後・解除後に削除される
- [x] #6 自動テストとREADMEが更新される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tauri: save_pasted_thumbnail（base64→一時ファイル、形式とサイズを検証）とdiscard_pasted_thumbnail（自分の一時ファイルのみ削除）を追加
2. lib/clipboard.tsでClipboardEventから画像を取り出しRustへ渡す
3. App: 保存パネル/コミット詳細表示中のpasteイベントを処理。テキスト欄へのテキスト貼り付けは妨げない
4. vitest・cargo testを追加、README更新
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Rust: save_pasted_thumbnail（base64を検証し一時フォルダのsprout-gui-paste-*/clipboard.<ext>へ書き出し）、discard_pasted_thumbnail（そのディレクトリ配下のみ削除）。
- フロント: windowのpasteで画像を含む場合だけpreventDefault。保存パネルとコミット詳細表示中のみ反応。
- 検証: pnpm test 57件、cargo test 6件、tsc --noEmit 成功。実機（Tauri/WebView2）での手動確認は未実施。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GUIで保存パネル・葉の詳細の表示中にCtrl+Vでクリップボード画像をサムネイルとして登録できるようにした。画像は一時ファイル経由でCLIへ渡し使用後に削除。非対応形式・2 MiB超は警告。テキスト貼り付けは従来どおり。自動テストとgui/README.mdを更新。実機での手動確認は未実施。
<!-- SECTION:FINAL_SUMMARY:END -->
