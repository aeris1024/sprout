---
id: TASK-94
title: GUIで枝の作成に失敗したときに現在位置を動かさないようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:53'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/App.tsx
  - gui/src/components/CommitPanel.tsx
  - src/sprout/cli.py
priority: high
type: bug
ordinal: 93000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
葉の詳細の「ここから枝を伸ばす」は、先に現在位置を対象の葉へ移動してから枝を作るため、既存の名前を指定するなどで枝の作成に失敗しても現在位置が移動したままになる。未保存の変更もつぼみへ移るが、通知には枝の作成に失敗したことしか表示されない。サンプルで「branch already exists: main」となった後、いまここが対象の葉へ移り、つぼみが1件増えることを確認した。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 既存の枝名など、枝の作成が拒否される場合は、現在位置・現在のブランチ・作業ファイル・つぼみが操作前と変わらない
- [ ] #2 枝の作成が成功した場合は、従来どおり新しい枝へ移動し、未保存の変更はつぼみとして残る
- [ ] #3 操作の途中で失敗して状態が変わった場合は、何が変わったかを通知で確認でき、マップと上部バーが実際の状態と一致する
- [ ] #4 失敗時は入力した枝名が残り、理由を確認して修正できる
- [ ] #5 自動テストで名前の重複、未保存の変更がある場合、途中失敗の動作を検証する
<!-- AC:END -->
