---
id: TASK-15
title: .sproutignoreで無視パターンを指定できるようにする
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-15 16:19'
updated_date: '2026-07-20 09:57'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
modified_files:
  - src/sprout/repository.py
  - tests/test_repository.py
  - README.md
priority: medium
type: feature
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

キャッシュや一時ファイル(例: `*.tmp`、`Thumbs.db`、ソフトの自動保存ファイル)が`status --untracked`の一覧を埋め、ディレクトリ単位の`track`で誤って登録される。除外パターンの仕組みが必要。

## 実装方針

1. プロジェクトルートの`.sproutignore`を読む。書式はgitignoreのサブセットで十分: 1行1パターン、`#`でコメント、glob(`fnmatch`)でパス全体とファイル名の両方に対して照合、`dir/`形式でディレクトリ配下全体を除外。標準ライブラリだけで実装するなら`fnmatch`+自前の行パースで足りる。gitignore完全互換にしたい場合はpathspecパッケージの採用を検討(依存追加の要否を判断する)。
2. 適用箇所は2つ:
   - `track`のディレクトリ走査(`os.walk`のループ内でファイル・ディレクトリを除外)
   - `untracked_files`(status --untrackedの一覧)
   ファイルを明示的にパス指定で`track`した場合は無視パターンより優先して登録する(gitと同様の感覚)。
3. 既に追跡中のファイルには影響しない(statusのadded/modified/deleted判定は変えない)。
4. `.sproutignore`自体は通常のファイルとして追跡可能にしておく(ユーザーが履歴管理したい場合があるため)。

READMEに書式と適用範囲を記載する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `.sproutignore`のパターンに一致するファイルがディレクトリ指定の`track`で除外される
- [x] #2 パターンに一致するファイルが`status --untracked`に表示されない
- [x] #3 ファイルを明示指定した`track`は無視パターンより優先される
- [x] #4 追跡済みファイルの変更検出には影響しない
- [x] #5 READMEに書式と挙動が記載されている
- [x] #6 パターン照合と適用範囲がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. `.sproutignore` を読み、`#` コメント / glob / `dir/` を解釈するヘルパーを追加（標準ライブラリ fnmatch）
2. ディレクトリ指定の `track` と `untracked_files` で無視パターンを適用する
3. ファイル明示の `track` は無視より優先する
4. README に書式と適用範囲を追記し、テストで検証する
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
実装: `.sproutignore` を fnmatch で解釈。ディレクトリ track と untracked_files に適用し、明示 track は優先。
検証: pytest → 59 passed, 2 skipped。
- AC1/2: test_sproutignore_skips_files_for_directory_track_and_untracked_listing
- AC3: test_sproutignore_explicit_track_overrides_patterns
- AC4: test_sproutignore_does_not_affect_tracked_status_detection
- AC5: README 追記
- AC6: 上記テスト
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`.sproutignore` で無視パターンを指定できるようにした。ディレクトリ track と status --untracked に適用し、明示的な track は優先。追跡済みの変更検出は不変。pytest 59 passed / 2 skipped で AC1–6 を確認。
<!-- SECTION:FINAL_SUMMARY:END -->
