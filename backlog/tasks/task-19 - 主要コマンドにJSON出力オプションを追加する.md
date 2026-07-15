---
id: TASK-19
title: 主要コマンドにJSON出力オプションを追加する
status: To Do
assignee: []
created_date: '2026-07-15 16:20'
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
- [ ] #1 `status --json`等で有効なJSONが出力される
- [ ] #2 JSON出力時に人間向けの装飾テキストが混ざらない
- [ ] #3 日本語パスがエスケープされず出力される(ensure_ascii=False)
- [ ] #4 READMEに出力スキーマが記載されている
- [ ] #5 各コマンドのJSON出力がテストで検証されている
<!-- AC:END -->
