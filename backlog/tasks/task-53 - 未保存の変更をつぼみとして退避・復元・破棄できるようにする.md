---
id: TASK-53
title: 未保存の変更をつぼみとして退避・復元・破棄できるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-27 15:03'
updated_date: '2026-10-27 15:44'
labels:
  - cli
  - gui-redesign
dependencies:
  - TASK-52
  - TASK-61
references:
  - src/sprout/repository.py
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: medium
type: feature
ordinal: 53000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

GUI刷新（doc-1、TASK-51）では、未保存の変更があるまま別のスナップショットへ移るとき、確認なしで変更を「つぼみ」として退避し、あとで戻れるようにする。

## ゴール

追跡ファイルの未保存の状態を、退避元の現在位置に紐づくつぼみとして保存し、一覧・復元・破棄できるようにする。つぼみの実体は既存のobjectsストアへ保存して重複排除を共有する。1つのスナップショットに複数のつぼみを付けられる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 追跡ファイルの未保存の状態を、退避元の現在位置・ブランチ・作成日時・変更ファイル情報とともにつぼみとして保存できる
- [x] #2 つぼみの一覧を人向け出力とJSONで取得でき、treeのJSONで各スナップショットに付いたつぼみを確認できる
- [x] #3 つぼみを復元すると作業ツリーが退避時の状態になり、現在位置が退避元になり、復元完了後にだけつぼみが削除される
- [x] #4 復元時に別の未保存の変更がある場合は、それを先に新しいつぼみとして退避してから復元する
- [x] #5 つぼみを破棄でき、破棄は明示的な指定がない限り行われない
- [x] #6 未追跡ファイルは退避・復元で削除も上書きもされず、衝突やリンクがある場合は復元を中止する既存の保護が適用される
- [x] #7 つぼみの実体がobjectsストアで重複排除され、gcが参照中のオブジェクトを削除せず、doctorとstatsがつぼみを検査・集計する
- [x] #8 READMEとJSON契約が更新され、退避、一覧、復元、破棄、中断時の復旧、gc・doctor・statsとの整合がテストされる
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. budsとbud_filesテーブルを新規リポジトリのスキーマに追加する。既存リポジトリはdiscover時にCREATE TABLE IF NOT EXISTSで追加し、必須テーブル検査には含めない（記録がなくても既存リポジトリを使い続ける方針に合わせる）。
2. 追跡ファイルの保存処理をcommitから切り出し、save_budで現在位置・ブランチ・作成日時とともに保存する。現在位置から変更がなければ拒否する。
3. restore_budは移動先の検証を先に行い、未保存の変更があれば新しいつぼみへ退避してから、つぼみの内容を全体restoreと同じ_materializeで書き戻し、現在位置を退避元にする。書き戻し完了後にだけつぼみを削除し、失敗時は直前に作った退避つぼみを取り消す。
4. drop_budで削除する。CLIは--yesがない限り削除しない。
5. CLIにbudコマンド（一覧・--save・--restore ID・--drop ID --yes、--json）を追加し、treeのJSONにbudsを含める。
6. gcの参照、doctorのオブジェクト検査と退避元の存在確認、statsのつぼみ数、pruneでの退避元コミットの保護に対応する。
7. README・JSON契約を更新し、退避・一覧・復元・破棄・中断復旧・gc/doctor/statsとの整合をテストする。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
未保存の変更を現在位置基準で判定するTASK-61を先に行うよう依存を追加した（2026-10-28 ユーザー指示）。

## 実装と検証（2026-10-28）
- buds・bud_filesテーブルを追加。既存リポジトリはdiscover時にCREATE TABLE IF NOT EXISTSで作成し、必須テーブル検査には含めない（記録のない既存リポジトリを使い続ける方針に合わせた）。
- commitの追跡ファイル保存処理を_store_tracked_filesへ切り出し、つぼみと共有。つぼみは作業フォルダを変更しない（--saveは保存のみ）。現在位置から変更がなければnothing_to_saveで拒否。
- restore_budは戻す先の検証とrestore計画の作成を先に行い、未保存の変更を新しいつぼみへ退避してから全体restoreと同じ_materializeで書き戻す。現在位置はつぼみの元、ブランチはつぼみ作成時のブランチ（存在すれば）。書き戻し完了後につぼみを削除。書き戻しが失敗し現在位置が変わっていなければ、直前に作った退避つぼみを取り消す。
- CLIはsprout bud（一覧）、--save、--restore BUD、--drop BUD --yes、--json。treeのJSONにbuds、statsにBuds行。
- gcはbud_filesを参照扱い、doctorはつぼみのオブジェクトと元コミットの存在を検査、pruneはつぼみの元コミットを保護（外部キーで削除失敗しないように）。
- 検証: pytest 244 passed, 19 skipped。中断時はrestore_safetyのテストで作業ファイル・現在位置・つぼみが保たれることを確認。git diff --check成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
未保存の変更をつぼみとして現在位置に紐づけて保存・一覧・復元・破棄できるようにした（sprout bud）。復元時は別の未保存変更を先に新しいつぼみへ退避し、書き戻し完了後にだけ元のつぼみを消す。gc・doctor・stats・prune・treeのJSONがつぼみを扱う。既存リポジトリは開いたときにテーブルを追加する。README更新、全244テスト成功（19件は環境条件でスキップ）で確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
