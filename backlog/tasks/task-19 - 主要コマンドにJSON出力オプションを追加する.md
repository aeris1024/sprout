---
id: TASK-19
title: 主要コマンドにJSON出力オプションを追加する
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:20'
updated_date: '2026-07-28 18:28'
labels: []
dependencies: []
references:
  - src/sprout/cli.py
priority: low
type: feature
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

`status`や`log`の出力は人間向けのテキストのみで、スクリプトや他ツールからの連携に使いにくい。

## 実装方針

`status`、`log`、`show`、`branch`(一覧)に`--json`オプションを追加する。

1. 各コマンドで、`--json`指定時は`json.dumps(..., ensure_ascii=False)`で構造化データを1つ出力する。人間向けの装飾行(`On branch ...`等)は混ぜない。
2. 出力スキーマ例:
   - `status`: `{"branch": "main", "changes": [{"state": "modified", "path": "a.bin"}], "tracked": [...], "untracked": [...]}`(tracked/untrackedはオプション指定時のみ)
   - `log`: `[{"id": "...", "parent_id": null, "created_at": "...", "message": "..."}]`
   - `show`: コミット情報+`files`配列(path, object_hash, size, mtime_ns)
   - `branch`: `[{"name": "main", "commit_id": "...", "comment": "", "current": true}]`
3. リポジトリ層は既に構造化データ(dataclass、Row)を返しているため、変換はCLI層で完結する。dataclassは`dataclasses.asdict`が使える。
4. READMEにスキーマの説明を追記する。スキーマは後方互換を意識し、キーの削除・改名をしない方針をREADMEに明記する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `status --json`等で有効なJSONが出力される
- [x] #2 JSON出力時に人間向けの装飾テキストが混ざらない
- [x] #3 日本語パスがエスケープされず出力される(ensure_ascii=False)
- [x] #4 READMEに出力スキーマが記載されている
- [x] #5 各コマンドのJSON出力がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. JSONをensure_ascii=Falseで1回だけ出力する共通関数と、status/log/show/branch一覧の構造化変換関数を追加する。 2. 各コマンドへ--jsonを追加し、既存の絞り込みオプションを反映する。statusのパスモードも構造化し、logでは--onelineとの併用、branchでは変更操作との併用を拒否する。 3. 各JSONスキーマ、日本語パス、装飾混入なし、競合オプションをCLIテストで検証する。 4. READMEにスキーマと後方互換方針を記載し、全体テストを実行する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
status/log/show/branch一覧へ--jsonを追加し、変換処理を将来のserveでも再利用できる関数へ分離した。status PATHもpaths配列で対応。logの--oneline、showの非UTC--timezone、branch変更操作との競合は明確に拒否する。READMEに全スキーマと後方互換方針を記載。全テスト: 78 passed, 2 skipped。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
status/log/show/branch一覧へ再利用可能なJSON出力を追加した。日本語を保持し、人間向け装飾を混ぜず、既存のパス・件数オプションも反映する。READMEに全スキーマと互換方針を記載し、全テスト78件成功・2件スキップで検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
