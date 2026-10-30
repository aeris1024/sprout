---
id: TASK-103
title: GUIから作業ファイルとプレビューを関連アプリで開けるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/SavePanel.tsx
  - gui/src/components/FilePanel.tsx
  - gui/src/components/PreviewPanel.tsx
  - gui/src-tauri/src/lib.rs
  - gui/src-tauri/capabilities/default.json
priority: medium
type: feature
ordinal: 102000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUIには作業ファイルを開く操作や、エクスプローラーで表示する操作がない。画像以外のプレビューは、いったん取り出さないと内容を確認できない。別のアプリで編集して戻る作業の中で、対象のファイルを探す手間が生じる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 未保存の変更と追跡ファイルから、関連アプリで開く操作とエクスプローラーで表示する操作を使える
- [ ] #2 プレビューを、取り出し先を指定せずに関連アプリで開ける。一時ファイルは履歴と作業フォルダに残らない
- [ ] #3 ファイルがない場合や開けない場合は理由を通知する
- [ ] #4 プロジェクト外のパスや、リンク経由の意図しない場所を開かない
- [ ] #5 自動テストで呼び出しと失敗時の動作を検証し、実機で確認して、gui/README.mdを更新する
<!-- AC:END -->
