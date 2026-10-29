---
id: TASK-54
title: 退避と移動を1回で行うgoコマンドを追加する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-27 15:03'
updated_date: '2026-10-27 15:53'
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
- [x] #1 未保存の変更がない場合、指定したスナップショットの内容を作業ツリーへ書き戻し、現在位置を更新する
- [x] #2 未保存の変更がある場合、確認や--discardなしで現在位置に紐づくつぼみへ退避してから移動する
- [x] #3 移動先が現在のブランチの先端なら現在のブランチを維持し、他のブランチの先端ならそのブランチへ切り替え、途中のスナップショットならブランチを変えない
- [x] #4 JSON出力が、移動後の現在位置、現在ブランチ、作成したつぼみ、作業ツリーの変更有無を1回の応答で返す
- [x] #5 退避と移動のどちらかの途中で中断しても、次回起動時に未保存の変更を失わない状態へ復旧する
- [x] #6 未追跡ファイルの衝突やリンクがある場合は、退避も移動も行わずに中止する
- [x] #7 READMEとJSON契約が更新され、各移動先の種類、退避あり・なし、中断復旧、衝突時の中止がテストされる
- [x] #8 既存の`sprout move`による追跡ファイルの移動の動作と出力が変わらない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. restore_budの「検証→未保存変更をつぼみへ退避→_materialize→失敗時に退避を取り消す」処理を共通化する。
2. Repository.goで移動先（コミット・ブランチ・タグ）を解決し、現在ブランチの先端ならブランチ維持、他ブランチの先端ならそのブランチ（ブランチ名指定ならそれ、なければ名前順で最初）へ切り替え、途中ならブランチを変えずに現在位置だけ移す。
3. CLIにsprout go TARGET [--json]を追加し、移動後の現在位置・ブランチ・先端かどうか・作成したつぼみ・作業ツリーの変更一覧を1回で返す。
4. README・JSON契約を更新し、各移動先、退避あり/なし、中断復旧、衝突時の中止、既存moveの非変更をテストする。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
既存の`sprout move`（追跡ファイルの移動）と名前が重なるため、スナップショット間を移動する新コマンドの名前をgoに決定した（2026-10-28 ユーザー決定）。

## 実装と検証（2026-10-28）
- restore_budと共通の_materialize_keeping_changes（移動先の検証とrestore計画→未保存変更をつぼみへ退避→_materialize→書き戻し前の失敗なら退避つぼみを取り消す）を追加し、Repository.goとsprout go TARGET [--json]を実装。
- ブランチ: 現在ブランチの先端なら維持、他ブランチの先端なら指定ブランチ名、なければ名前順で最初へ切り替え、途中ならブランチ維持で現在位置のみ移動。
- JSONはcurrent_commit・branch・at_branch_tip・bud・changesを1回で返す。
- 中断: 退避はDB挿入1回で、書き戻し中の中断は次回起動時に巻き戻され、退避つぼみは取り消される（restore_safetyのテスト）。退避の確定後・書き戻し前の中断でも変更はつぼみと作業ツリーの両方に残り失われない。
- 検証: pytest 257 passed, 19 skipped。既存のsprout moveの既存テストとRepository.moveのテストが成功。git diff --check成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
未保存の変更をつぼみとして退避してから指定スナップショットへ移動するsprout goを追加した。移動先に応じてブランチを維持・切り替えし、JSONで移動後の現在位置・ブランチ・先端かどうか・作成したつぼみ・変更一覧を1回で返す。衝突時は何も変更せず中止し、中断時は復旧する。restore_budと処理を共通化。README更新、全257テスト成功で確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
