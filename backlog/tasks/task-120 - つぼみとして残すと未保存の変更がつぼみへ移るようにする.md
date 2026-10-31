---
id: TASK-120
title: つぼみとして残すと未保存の変更がつぼみへ移るようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-31 05:31'
updated_date: '2026-10-31 05:40'
labels:
  - gui
  - cli
dependencies: []
priority: medium
ordinal: 119000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
bud --save とGUIの「つぼみとして残す」は作業ファイルを変えないため、未保存の芽とつぼみが並び、その後に移動すると同じ内容のつぼみがもう1つできる。つぼみを捨てても変更が残るのも分かりにくい。実行すると変更がつぼみへ移り、作業フォルダが現在位置の内容へ戻るようにする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 bud --save で未保存の変更がつぼみへ移り、追跡ファイルが現在位置の内容へ戻る。未追跡ファイルは変更しない
- [x] #2 bud --save --keep-files では作業ファイルを変更しない
- [x] #3 実行後に別の葉へ移動してもつぼみが増えず、このつぼみに戻ると元の変更と追跡状態に戻る
- [x] #4 失敗時は作業ファイルとつぼみを変更しない。最初の保存前でも変更を失わない
- [x] #5 GUIの表示と通知、自動テスト、README.md、gui/README.mdを新しい動作に合わせる
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. repositoryにmove_changes_to_budを追加し、go と同じ退避と書き戻しの経路を使う 2. bud --save をこの動作に変更し --keep-files を追加 3. GUIの説明・通知・テストを更新 4. READMEを更新
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
repositoryのmove_changes_to_budはgoと同じ_materialize_keeping_changesを使う。既存のsave_budは--keep-files用に残した。pytest 607件成功(追加テスト前の全体実行)、vitest 181件とtsc成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
bud --saveとGUIの「つぼみとして残す」で、未保存の変更がつぼみへ移り作業フォルダが現在位置へ戻るようにした。移動してもつぼみが増えない。作業ファイルを残す--keep-filesを追加。リポジトリ・CLI・GUIのテストとREADMEを更新し、pytest・vitest・tscが成功。
<!-- SECTION:FINAL_SUMMARY:END -->
