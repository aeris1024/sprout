---
id: TASK-28
title: コミットに後付けのメモとラベルを付けられるようにする
status: To Do
assignee: []
created_date: '2026-07-15 16:39'
updated_date: '2026-07-15 16:39'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: low
type: feature
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

コミットメッセージは作成時に固定されるため、「提出した版」「ボツ」「クライアントOK」のような後から分かる情報を記録する場所がない。編集可能なメモとラベルがあると、GUIのツリービューでの絞り込み・色分けや、CLIでの検索に使える。タグ(TASK-14)は不変の目印、こちらは編集可能な注記という役割分担。

## 実装方針

### スキーマ

- `commit_notes(commit_id TEXT PRIMARY KEY REFERENCES commits(id) ON DELETE CASCADE, note TEXT NOT NULL, updated_at TEXT NOT NULL)`
- `commit_labels(commit_id TEXT NOT NULL REFERENCES commits(id) ON DELETE CASCADE, label TEXT NOT NULL, PRIMARY KEY (commit_id, label))`

どちらも`CREATE TABLE IF NOT EXISTS`での追加。ラベルは自由文字列(空・空白のみは拒否)で、事前定義は不要。

### CLI

- `sprout note COMMIT MESSAGE`: メモを設定(上書き)。`--delete`で削除。`show`でメモを表示する。
- `sprout label COMMIT NAME...`: ラベルを追加。`--remove NAME`で外す。`show`と`log`(あれば`tree`)にラベルを表示する。
- `sprout log --label NAME`: 指定ラベルの付いたコミットだけに絞り込むオプションを追加する。
- 書き込みは`@locked`で行う。

### 他タスクとの関係

`tree --json`(TASK-22)が実装済みの場合、コミット要素に`labels`と`note`を含めるよう更新する(GUIの色分け・絞り込みで使うため)。READMEに使い方を追記する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 コミットへのメモの設定・上書き・削除ができる
- [ ] #2 コミットへのラベルの追加・削除ができる
- [ ] #3 `show`でメモとラベルが確認できる
- [ ] #4 `log`をラベルで絞り込める
- [ ] #5 tree --jsonが存在する場合、メモとラベルが出力に含まれる
- [ ] #6 READMEが更新され、メモ・ラベルの操作がテストで検証されている
<!-- AC:END -->
