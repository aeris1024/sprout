---
id: TASK-17
title: ブランチの削除とリネームをできるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:19'
updated_date: '2026-07-28 18:48'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: low
type: feature
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

ブランチは作成しかできず、不要になった実験ブランチを消したり名前を変えたりする手段がない。

## 実装方針

`branch`コマンドに`--delete NAME`と`--rename OLD NEW`(または`--rename NEW`を位置引数と併用)を追加する。リポジトリ層に`delete_branch(name)`と`rename_branch(old, new)`を`@locked`で追加する。

- 削除: 現在のブランチ(head_branch)は削除不可。ブランチが指すコミットは残る(コミット削除は行わない。到達不能になったコミットの扱いはgcタスクの範囲外で、`commits.branch_name`は参照情報にすぎない)。
- リネーム: 新名称は`create_branch`と同じ検証(空・空白・先頭ハイフン・hexプレフィックス禁止、重複禁止)を通す。現在のブランチをリネームした場合はmetaの`head_branch`も更新する。
- 既存の`--comment`/`--set-comment`との排他チェックを`branch`コマンド内で行う。

READMEのコマンド一覧を更新する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ブランチを削除できる(現在のブランチは削除不可)
- [x] #2 ブランチをリネームでき、現在のブランチの場合はHEADも追従する
- [x] #3 不正な新名称や重複はエラーになる
- [x] #4 READMEが更新されている
- [x] #5 削除・リネーム・エラー系がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. ブランチ名検証を共通ヘルパーへ抽出し、create/renameで共有する。 2. @lockedなdelete_branchとrename_branchを追加し、現在ブランチ削除禁止・重複/不正名拒否・HEAD追従を実装する。 3. CLIはユーザー決定どおりbranch --delete NAMEとbranch OLD --rename NEWを採用し、既存オプションとの排他を検証する。 4. Repository/CLIテストとREADMEを更新し、全体テスト後に完了・コミットする。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ブランチ名検証を共通化し、@lockedなdelete_branch/rename_branchを実装。CLIはbranch --delete NAMEとbranch OLD --rename NEWを採用し、既存操作との排他を追加した。READMEを更新。全テスト: 81 passed, 2 skipped。
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @codex
created: 2026-07-28 18:46
---
CLI構文はユーザー判断により、削除を branch --delete NAME、リネームを branch OLD --rename NEW とする。
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
ブランチの削除とリネームをRepository/CLIへ追加し、現在ブランチ削除禁止、HEAD追従、名前検証と操作排他を実装した。READMEを更新し、全テスト81件成功・2件スキップで正常系とエラー系を検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
