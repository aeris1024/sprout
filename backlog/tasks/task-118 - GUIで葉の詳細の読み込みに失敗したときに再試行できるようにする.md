---
id: TASK-118
title: GUIで葉の詳細の読み込みに失敗したときに再試行できるようにする
status: To Do
assignee: []
created_date: '2026-10-30 21:29'
labels:
  - gui
dependencies: []
references:
  - gui/src/App.tsx
priority: medium
type: bug
ordinal: 117000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`sprout show`が失敗すると、エラー通知は出るが葉の選択が残り、右パネルが「読み込み中…」のまま止まる。読み込みが終わっていないものとして扱われるため、ドロップも受け付けない。通知を閉じると、失敗したことも画面から分からなくなる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 読み込みに失敗すると「読み込み中…」を表示し続けず、失敗したことと理由がパネルで分かる
- [ ] #2 パネルから再試行でき、成功すると葉の詳細を表示する
- [ ] #3 別の葉を選ぶか詳細を閉じると、失敗の表示が消えて通常の操作に戻れる
- [ ] #4 読み込み中の表示と失敗の表示を区別し、失敗中のドロップと貼り付けで葉を変更しない
- [ ] #5 自動テストで失敗、再試行、別の葉の選択を検証する
<!-- AC:END -->
