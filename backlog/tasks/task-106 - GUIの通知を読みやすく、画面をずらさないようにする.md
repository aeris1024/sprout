---
id: TASK-106
title: GUIの通知を読みやすく、画面をずらさないようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
updated_date: '2026-10-31 09:30'
labels:
  - gui
  - usability
dependencies:
  - TASK-124
references:
  - gui/src/App.tsx
  - gui/src/App.css
  - gui/src/lib/sprout.ts
  - gui/README.md
  - gui/src/lib/cliErrors.ts
priority: medium
type: enhancement
ordinal: 105000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
通知の表示でマップが上下に動くこと、成功通知が残り続けること、葉を選ぶとエラーが消えることを改善する。
主なCLIエラーのGUI向け日本語化はTASK-124で実装済みであり、本タスクで翻訳機構を重複実装しない。既存のcliErrorsの対応表と用語を維持し、未対応エラーも元のメッセージやcodeを必要時に確認できるようにする。
通知の配置・保持時間・閉じる操作と支援技術への通知を担当する。CLI再編後もエラーcodeを基準に扱い、英語メッセージの文字列一致に依存しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 通知の表示と消去でマップとパネルの位置がずれない
- [ ] #2 成功の通知は一定時間で消え、エラーと警告は確認するまで残る。葉の選択だけではエラーが消えない
- [ ] #3 TASK-124の日本語エラー対応と用語を維持し、未対応エラーも元のメッセージとcodeを確認できる。新しい翻訳方式を重複実装しない
- [ ] #4 通知は支援技術に伝わり、キーボードで閉じられる
- [ ] #5 自動テストで表示時間、選択時の維持、エラーの表示を検証し、gui/README.mdを更新する
<!-- AC:END -->
