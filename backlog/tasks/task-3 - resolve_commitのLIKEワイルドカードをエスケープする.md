---
id: TASK-3
title: resolve_commitのLIKEワイルドカードをエスケープする
status: To Do
assignee: []
created_date: '2026-07-15 16:14'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
priority: medium
type: bug
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 問題

`resolve_commit`はコミットIDの前方一致検索に `SELECT id FROM commits WHERE id LIKE ?` を `value + "%"` で実行している。入力に `%` や `_` が含まれるとSQLのワイルドカードとして解釈され、意図しないマッチが起きる(例: `sprout show %` は全コミットにマッチして ambiguous エラーになる)。

## 修正方針

コミットIDはuuid4のhex(小文字の16進数)なので、ブランチ名として解決できなかった値を前方一致検索へ回す前に `^[0-9a-f]+$` で検証し、該当しなければ即 `unknown commit` エラーにするのが最も単純。あるいは `LIKE ? ESCAPE` 句で `%` `_` `\` をエスケープしてもよい。どちらの場合も、既存の正常系(完全ID、先頭プレフィックス、ブランチ名)の解決動作は変えないこと。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `%`や`_`を含む入力がワイルドカードとして解釈されない
- [ ] #2 完全ID・IDプレフィックス・ブランチ名による解決は従来どおり動作する
- [ ] #3 ワイルドカード文字を含む入力に対するテストが追加されている
<!-- AC:END -->
