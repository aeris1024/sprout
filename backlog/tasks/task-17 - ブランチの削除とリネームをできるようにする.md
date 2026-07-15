---
id: TASK-17
title: ブランチの削除とリネームをできるようにする
status: To Do
assignee: []
created_date: '2026-07-15 16:19'
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
- [ ] #1 ブランチを削除できる(現在のブランチは削除不可)
- [ ] #2 ブランチをリネームでき、現在のブランチの場合はHEADも追従する
- [ ] #3 不正な新名称や重複はエラーになる
- [ ] #4 READMEが更新されている
- [ ] #5 削除・リネーム・エラー系がテストで検証されている
<!-- AC:END -->
