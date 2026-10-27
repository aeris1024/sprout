---
id: TASK-61
title: statusなどの変更判定を作業ツリーの現在位置と比べるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-27 15:32'
updated_date: '2026-10-27 15:37'
labels:
  - cli
  - gui-redesign
dependencies:
  - TASK-52
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: medium
type: enhancement
ordinal: 61000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

TASK-52で作業ツリーの現在位置（基づいているスナップショット）を記録するようになった。しかし、statusの変更一覧、引数なしのdiff、未保存の変更の判定は、今も現在ブランチの先端と比べている。そのため、restoreで過去のスナップショットへ移動した直後は、何も編集していなくてもstatusにmodifiedなどが表示される。GUI刷新（doc-1）では、未保存の変更の有無が上部バーの表示、未保存の芽、つぼみへの自動退避の判断に直結するため、現在位置を基準にする必要がある。

## ゴール

作業ツリーの変更を判定する処理の比較相手を、ブランチ先端から現在位置へ変える。ブランチ先端にいる場合の結果は従来と変わらない。途中のスナップショットからの保存（commitの親や、変更がないときの扱い）はTASK-55で扱う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 過去のスナップショットへ全体restoreした直後、ファイルを編集していなければstatusの変更一覧が空になり、人向け表示はWorking tree cleanになる
- [x] #2 現在位置からファイルを追加・変更・削除すると、statusにそれぞれadded・modified・deletedとして表示される
- [x] #3 引数なしのdiffが、ブランチ先端ではなく現在位置と作業ツリーを比べる
- [x] #4 restore・switch・branch --switchの未保存の変更の判定が現在位置を基準に行われ、現在位置から変更がなければ--discardなしで別のスナップショットへ移動できる
- [x] #5 現在位置がブランチ先端のとき、および現在位置の記録がない既存リポジトリでは、status・diff・未保存の変更の判定の結果が従来と同じになる
- [x] #6 statusのJSONとGUIが表示する変更件数が現在位置を基準にした値になり、READMEの説明が更新される
- [x] #7 先端・過去のスナップショット・編集あり・編集なし・記録なしの各場合がテストされる
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Repository.status、引数なしdiff、_has_unsaved_changes、全体restore時の入力検証が比較に使うマニフェストを、head_commitではなくcurrent_commit（記録がなければブランチ先端）にする。
2. log・commitの親・tag省略時の対象・pruneの内容一致チェックは範囲外として変更しない（commitはTASK-55）。
3. README（status・diff・未保存変更の説明）を現在位置基準に更新する。
4. 先端・過去のスナップショット・編集あり/なし・記録なしの各場合をRepositoryとCLIでテストし、全テストを通す。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
status・引数なしdiff・_has_unsaved_changes・全体restoreの入力検証の比較対象をcurrent_commitへ変更。current_commitは記録がなければブランチ先端を返すため、先端・既存リポジトリでは従来と同じ。GUIの変更件数はstatus --jsonのchangesをそのまま使うため追加変更なし。既存テストtest_commit_multiple_files_restore_and_deduplicateは、過去スナップショットへのrestore直後にstatusが空になる新仕様へ期待値を更新。検証: pytest 233 passed, 19 skipped。git diff --check成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
status・引数なしdiff・移動前の未保存変更の判定を、ブランチ先端ではなく記録した現在位置と比べるようにした。過去のスナップショットへ移った直後は変更なしとなり、編集しなければ--discardなしで移動できる。先端と記録のない既存リポジトリでは従来どおり。READMEを更新し、Repository/CLIテストを追加して全233テスト成功で確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
