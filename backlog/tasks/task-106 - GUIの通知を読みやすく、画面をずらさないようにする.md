---
id: TASK-106
title: GUIの通知を読みやすく、画面をずらさないようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/App.tsx
  - gui/src/App.css
  - gui/src/lib/sprout.ts
  - gui/README.md
priority: medium
type: enhancement
ordinal: 105000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
通知を表示するとマップが74px下へずれ、ポインタの下の内容が動く。成功の通知も閉じるまで残る。CLIのエラーは「branch already exists: main」「nothing to commit」のように英語のまま表示される。一方でエラーは葉を1回クリックするだけで消え、読み返せない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 通知の表示と消去でマップとパネルの位置がずれない
- [ ] #2 成功の通知は一定時間で消え、エラーと警告は確認するまで残る。葉の選択だけではエラーが消えない
- [ ] #3 主なCLIエラーが日本語の説明で表示され、未対応のエラーも元のメッセージとコードを確認できる
- [ ] #4 通知は支援技術に伝わり、キーボードで閉じられる
- [ ] #5 自動テストで表示時間、選択時の維持、エラーの表示を検証し、gui/README.mdを更新する
<!-- AC:END -->
