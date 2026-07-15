---
id: TASK-14
title: タグ(名前付きスナップショット)を追加する
status: To Do
assignee: []
created_date: '2026-07-15 16:18'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: medium
type: feature
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

「提出版」「納品版」のような目印をコミットに付ける手段がない。ブランチで代用できるが、ブランチは先端が動くもので用途が異なる。

## 実装方針

1. スキーマに`tags`テーブルを追加する: `name TEXT PRIMARY KEY, commit_id TEXT NOT NULL REFERENCES commits(id), comment TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL`。`SCHEMA_VERSION`の扱いは、既存DBに`CREATE TABLE IF NOT EXISTS`で追加するだけなら互換性が保てるためバージョン据え置きでもよい(他のスキーマ変更タスクと同時に行う場合はまとめて上げる)。
2. CLI: `sprout tag`(一覧)、`sprout tag NAME [COMMIT] [-m COMMENT]`(作成、COMMIT省略時はHEAD)、`sprout tag --delete NAME`(削除)。`branch`コマンドの実装が良い雛形になる。
3. 名前の検証は`create_branch`と同じ規則(空・空白・先頭ハイフン禁止、hexプレフィックスに見える名前の禁止)を関数化して共有する。ブランチ名との重複も禁止する(`resolve_commit`の解決順が曖昧になるため)。
4. `resolve_commit`でタグ名も解決できるようにする(解決順: ブランチ → タグ → IDプレフィックス)。
5. タグはコミットを参照するため、gc実装(存在する場合)の参照集合に影響はない(commit_files経由で参照が保たれる)。

READMEにタグの説明とコマンド一覧の行を追加する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 HEADまたは指定コミットにタグを作成できる
- [ ] #2 タグの一覧表示と削除ができる
- [ ] #3 `show`や`restore`でタグ名によりコミットを指定できる
- [ ] #4 ブランチ名と重複するタグ名は拒否される
- [ ] #5 READMEにタグの使い方が追記されている
- [ ] #6 タグの作成・解決・削除・名前検証がテストで検証されている
<!-- AC:END -->
