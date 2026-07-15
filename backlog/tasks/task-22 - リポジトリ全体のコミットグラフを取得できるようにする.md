---
id: TASK-22
title: リポジトリ全体のコミットグラフを取得できるようにする
status: To Do
assignee: []
created_date: '2026-07-15 16:27'
labels: []
dependencies:
  - TASK-19
  - TASK-21
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: medium
type: feature
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

現在の`log`はHEADから親を遡る単線の履歴しか見えない。GUIでリポジトリ全体をツリー構造で俯瞰するために、全コミット・親子関係・ブランチ先端・サムネイル有無をまとめて取得できるAPIとコマンドが必要。

## 実装方針

### リポジトリ層

`Repository.graph()`を追加し、以下を一括で返す:

- 全コミット: `SELECT id, parent_id, branch_name, created_at, message FROM commits`(1クエリ)
- 全ブランチ: name, commit_id, comment
- タグ(TASK-14実装済みの場合): name, commit_id
- サムネイルのメタ情報(TASK-21): commit_idごとのmedia_typeとsize(実体のバイト列は含めない)

子リストはCLI/GUI側で`parent_id`から組み立てられるため、DB層は平坦なリストで返せば十分。

### CLI

`sprout tree`コマンドを追加する:

- 人間向け表示: created_at順に走査し、親子関係をインデントと罫線で表現する簡易ツリー。各行に`ID先頭12桁 メッセージ`、ブランチ先端には`[main]`のような注記、サムネイル付きには目印を付ける。
- `--json`: `{"commits": [{"id", "parent_id", "branch_name", "created_at", "message", "thumbnail": {"media_type", "size"} | null}], "branches": [...], "tags": [...]}`の形で出力する。GUIはこの出力だけでツリーを描画できることをゴールとする。

READMEのコマンド一覧に追記し、JSONスキーマを記載する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `sprout tree`で全ブランチのコミットが親子関係つきで表示される
- [ ] #2 `tree --json`で全コミット・親子関係・ブランチ・サムネイル有無を含むJSONが得られる
- [ ] #3 分岐した履歴(複数ブランチ)が正しく表現される
- [ ] #4 READMEにコマンドとJSONスキーマが記載されている
- [ ] #5 分岐を含むリポジトリでの出力がテストで検証されている
<!-- AC:END -->
