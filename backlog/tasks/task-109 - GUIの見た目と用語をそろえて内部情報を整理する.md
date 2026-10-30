---
id: TASK-109
title: GUIの見た目と用語をそろえて内部情報を整理する
status: To Do
assignee: []
created_date: '2026-10-30 17:55'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/App.css
  - gui/src/components/PreviewPanel.tsx
  - gui/src/components/TrashPanel.tsx
  - gui/README.md
priority: low
type: enhancement
ordinal: 108000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
プレビューとゴミ箱のボタンだけブラウザ標準の見た目で、↓ボタンが折り返し、「完全削除」も危険な操作に見えない。ゴミ箱には「2026-10-30T17:40:57.436230+00:00」のような時刻や内部IDがそのまま表示される。コミット、スナップショット、葉、芽、SNAPSHOT、BUDが同じ画面に混在している。gui/README.mdのマップ（縦に伸びる説明）と配色名の説明も現在の画面と異なる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 プレビューとゴミ箱のボタンが他の画面と同じ見た目になり、行内で不自然に折り返さない。完全削除など取り消せない操作が危険な操作として区別される
- [ ] #2 ゴミ箱の日時がローカル時刻の読みやすい形式で表示され、内部IDは必要なときに確認できる
- [ ] #3 画面と通知で使う用語の対応を定義し、英語の見出しを含めて統一する
- [ ] #4 タグ札といまここ札が重ならない
- [ ] #5 gui/README.mdのマップと配色の説明が現在の画面と一致する
- [ ] #6 既存の自動テストを更新し、ライトとダークの両方で表示を確認する
<!-- AC:END -->
