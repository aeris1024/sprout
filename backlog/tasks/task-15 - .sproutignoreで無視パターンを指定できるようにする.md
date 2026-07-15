---
id: TASK-15
title: .sproutignoreで無視パターンを指定できるようにする
status: To Do
assignee: []
created_date: '2026-07-15 16:19'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
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
- [ ] #1 `.sproutignore`のパターンに一致するファイルがディレクトリ指定の`track`で除外される
- [ ] #2 パターンに一致するファイルが`status --untracked`に表示されない
- [ ] #3 ファイルを明示指定した`track`は無視パターンより優先される
- [ ] #4 追跡済みファイルの変更検出には影響しない
- [ ] #5 READMEに書式と挙動が記載されている
- [ ] #6 パターン照合と適用範囲がテストで検証されている
<!-- AC:END -->
