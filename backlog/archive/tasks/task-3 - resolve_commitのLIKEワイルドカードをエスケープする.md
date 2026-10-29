---
id: TASK-3
title: resolve_commitのLIKEワイルドカードをエスケープする
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-15 16:14'
updated_date: '2026-07-19 19:17'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
modified_files:
  - src/sprout/repository.py
  - tests/test_repository.py
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
- [x] #1 `%`や`_`を含む入力がワイルドカードとして解釈されない
- [x] #2 完全ID・IDプレフィックス・ブランチ名による解決は従来どおり動作する
- [x] #3 ワイルドカード文字を含む入力に対するテストが追加されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. ブランチ解決後、コミット参照を小文字16進文字列として検証する。
2. ワイルドカード入力と既存の完全ID・プレフィックス・ブランチ解決をテストする。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ブランチ解決後のコミット参照を小文字16進文字列に限定し、SQL LIKEへワイルドカード入力を渡さないようにした。検証: uv run pytest (41 passed, 2 skipped)。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
コミット参照を事前検証して%と_のワイルドカード解釈を防止し、完全ID・プレフィックス・ブランチ名の回帰テストを追加した。全テスト成功。
<!-- SECTION:FINAL_SUMMARY:END -->
