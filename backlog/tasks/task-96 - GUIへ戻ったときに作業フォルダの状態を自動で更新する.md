---
id: TASK-96
title: GUIへ戻ったときに作業フォルダの状態を自動で更新する
status: To Do
assignee: []
created_date: '2026-10-30 17:53'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/App.tsx
  - gui/README.md
priority: high
type: enhancement
ordinal: 95000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
別のアプリでファイルを編集してGUIへ戻っても、「更新」を押すまで上部バーは「保存済み」のままで、未保存の変更も表示されない。別のアプリで編集して戻る使い方が中心のため、実際と異なる状態を信じて操作する原因になる。常時のファイル監視や自動スナップショットはTASK-30で扱い、本件はウィンドウへ戻ったときの再取得に限る。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ウィンドウがフォーカスを取り戻すと、未保存の変更と追跡状態、上部バー、マップが最新になる
- [ ] #2 他の操作の実行中は割り込まず、操作の結果を壊さない。短時間にフォーカスが繰り返し変わっても再取得が過剰に走らない
- [ ] #3 再取得で選択中の葉、入力中のメッセージやメモ、マップのスクロール位置が失われない
- [ ] #4 CLIのロックなどで再取得できない場合に、操作を妨げるエラーを繰り返し表示しない
- [ ] #5 自動テストでフォーカス時の更新、操作中の抑止、入力内容の維持を検証し、gui/README.mdを更新する
<!-- AC:END -->
