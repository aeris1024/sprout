---
id: TASK-125.9
title: 移動系をgoへ統合して全体移動と部分復元の役割を分ける
status: To Do
assignee: []
created_date: '2026-10-31 07:33'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
  - TASK-125.3
  - TASK-125.4
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - gui/src/App.tsx
  - tests/test_cli.py
  - tests/test_serve.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 133000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
名前・配置の変更だけではなく、現在のgo、switch、パスなしrestoreという全体移動の重複を解消する。正規の全体移動をトップレベルgoへ集約し、ファイル指定の復元はfile restoreへ分離する。branch switchとleaf restoreを正規の別入口として増設しない。手打ち用switchはgoの明示的なブランチ指定へのaliasとする。
未保存変更は安全な既定動作としてつぼみへ退避する。現在のgoを単純に別名化すると、同じ先端を共有する複数ブランチ、指定ブランチの選択、空のブランチ、全体restoreのブランチを保つ動作等が失われるため、差分を整理してから統合する。従来の変更時拒否・明示破棄・ブランチを保った全体復元を統合先でどう扱うかと具体的オプション名は、実装前にユーザーと確認する。今回のタスク登録で未確認の挙動変更を確定しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 goを全体移動の正規入口、file restore LEAF PATH...を部分復元の入口として整理し、branch switchとleaf restoreの重複した正規入口を残さない
- [ ] #2 未保存変更は既定でつぼみに退避し、移動失敗時に作業ファイル・現在位置・ブランチ・つぼみを部分的に変更しない
- [ ] #3 ブランチを明示して移動したときは同じ先端を共有する別ブランチがあっても指定したブランチを選べ、空ブランチ・途中の葉への移動の扱いを明文化して検証する
- [ ] #4 現在のgo/switch/全体restoreの動作差と、拒否・discard・ブランチを保つ復元の統合方針を実装前にユーザーと確認し、機能の消失や既定のデータ破棄を黙って導入しない
- [ ] #5 file restoreは選択外の作業ファイル・現在位置・ブランチ先端を変更しない。branch createの作成後移動も同じ移動方針と失敗時の整合を保つ
- [ ] #6 正規CLI、switch alias、serve、GUIの移動操作で決定した方針が一致し、V1保存形式を変更しない
<!-- AC:END -->
