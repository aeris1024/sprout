---
id: TASK-118
title: GUIで葉の詳細の読み込みに失敗したときに再試行できるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 21:29'
updated_date: '2026-10-30 21:49'
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
- [x] #1 読み込みに失敗すると「読み込み中…」を表示し続けず、失敗したことと理由がパネルで分かる
- [x] #2 パネルから再試行でき、成功すると葉の詳細を表示する
- [x] #3 別の葉を選ぶか詳細を閉じると、失敗の表示が消えて通常の操作に戻れる
- [x] #4 読み込み中の表示と失敗の表示を区別し、失敗中のドロップと貼り付けで葉を変更しない
- [x] #5 自動テストで失敗、再試行、別の葉の選択を検証する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Keep the load failure per leaf in App state. 2. Show the reason and a retry in the panel instead of loading text. 3. Clear it on selecting or closing. 4. Tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Load failures are kept per leaf and shown in the panel. A failed leaf stays in the loading state for drops and pastes, which TASK-97 already blocks.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A failed leaf load now shows its reason and a retry instead of loading forever, and clears on selecting or closing. Verified with 5 App tests and 169 GUI tests plus the build.
<!-- SECTION:FINAL_SUMMARY:END -->
