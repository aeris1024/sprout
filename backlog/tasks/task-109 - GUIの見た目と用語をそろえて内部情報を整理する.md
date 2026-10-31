---
id: TASK-109
title: GUIの見た目と用語をそろえて内部情報を整理する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 17:55'
updated_date: '2026-10-31 06:02'
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
- [x] #1 プレビューとゴミ箱のボタンが他の画面と同じ見た目になり、行内で不自然に折り返さない。完全削除など取り消せない操作が危険な操作として区別される
- [x] #2 ゴミ箱の日時がローカル時刻の読みやすい形式で表示され、内部IDは必要なときに確認できる
- [x] #3 画面と通知で使う用語の対応を定義し、英語の見出しを含めて統一する
- [x] #4 タグ札といまここ札が重ならない
- [x] #5 gui/README.mdのマップと配色の説明が現在の画面と一致する
- [x] #6 既存の自動テストを更新し、ライトとダークの両方で表示を確認する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 用語を葉・つぼみ・ブランチ等へ統一し、対応表をgui/README.mdに定義する。英語の見出しも日本語にする
2. プレビューとゴミ箱のボタンを共通スタイルにし、↑↓は名前の行へ移して折り返さないようにする
3. 取り消せない操作用の見た目を追加し、完全削除に適用する
4. ゴミ箱の日時をローカル形式にし、内部IDは折りたたむ
5. いまここ札をタグ札と重なるときだけ上へずらす
6. READMEのマップと配色の説明を実画面に合わせ、ライト・ダーク両方で確認する
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
用語は葉・メッセージ・ブランチ・つぼみ・未保存の芽・いまここ・プレビューに統一し、gui/README.mdの用語の節に対応表を置いた。terms.test.tsでGUIのソースに旧用語と英語の見出しが戻らないことを検査する。残る制限: CLIが返す英語のエラー文（unknown commitなど）とアーカイブHTMLのコミット表記はGUIの外なので変更していない。ライトとダークはCLI接続の開発画面で表示を確認し、いまここ札とタグ札の矩形が重ならないことをDOM計測で確認した。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
プレビューとゴミ箱のボタンを共通スタイルにし、↑↓を名前の行へ移して折り返しをなくした。完全削除は塗りつぶしの赤で区別した。ゴミ箱の日時をローカル時刻にし内部IDを折りたたんだ。用語を統一して対応表を定義し、いまここ札をタグ札と重なるときは葉の上へずらし、READMEのマップと配色の説明を実画面に合わせた。vitest 212件、tsc、vite build、cargo test 成功、CLI接続の開発画面でライトとダークを確認した。CLIの英語エラー文は対象外。
<!-- SECTION:FINAL_SUMMARY:END -->
