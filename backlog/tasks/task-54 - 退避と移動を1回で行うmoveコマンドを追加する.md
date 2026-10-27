---
id: TASK-54
title: 退避と移動を1回で行うgoコマンドを追加する
status: To Do
assignee: []
created_date: '2026-10-27 15:03'
updated_date: '2026-10-27 15:16'
labels:
  - cli
  - gui-redesign
dependencies:
  - TASK-52
  - TASK-53
references:
  - src/sprout/repository.py
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: medium
type: feature
ordinal: 54000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

GUI刷新（doc-1、TASK-51）では、芽のマップで「ここへ移動」を押すだけで、未保存の変更の退避と移動を確認なしで行う。現在のGUIは1回の復元でCLIを5回呼んでおり、体感で約2秒かかる（TASK-51の計測）。

## ゴール

指定したスナップショットへ移動するgoコマンド（`sprout go <コミット>`）を追加する。既存の`sprout move`は追跡ファイルの移動に使われているため、名前を分ける。未保存の変更があれば先につぼみへ退避し、移動先がブランチ先端ならそのブランチへ切り替え、途中のスナップショットならブランチを変えずに現在位置だけを移す。移動後にGUIが必要とする状態を1回の応答で返す。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 未保存の変更がない場合、指定したスナップショットの内容を作業ツリーへ書き戻し、現在位置を更新する
- [ ] #2 未保存の変更がある場合、確認や--discardなしで現在位置に紐づくつぼみへ退避してから移動する
- [ ] #3 移動先が現在のブランチの先端なら現在のブランチを維持し、他のブランチの先端ならそのブランチへ切り替え、途中のスナップショットならブランチを変えない
- [ ] #4 JSON出力が、移動後の現在位置、現在ブランチ、作成したつぼみ、作業ツリーの変更有無を1回の応答で返す
- [ ] #5 退避と移動のどちらかの途中で中断しても、次回起動時に未保存の変更を失わない状態へ復旧する
- [ ] #6 未追跡ファイルの衝突やリンクがある場合は、退避も移動も行わずに中止する
- [ ] #7 READMEとJSON契約が更新され、各移動先の種類、退避あり・なし、中断復旧、衝突時の中止がテストされる
- [ ] #8 既存の`sprout move`による追跡ファイルの移動の動作と出力が変わらない
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
既存の`sprout move`（追跡ファイルの移動）と名前が重なるため、スナップショット間を移動する新コマンドの名前をgoに決定した（2026-10-28 ユーザー決定）。
<!-- SECTION:NOTES:END -->
