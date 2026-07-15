---
id: TASK-27
title: cat/exportコマンドで作業ツリーを触らずコミット内ファイルを取り出せるようにする
status: To Do
assignee: []
created_date: '2026-07-15 16:38'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: low
type: feature
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

コミット内のファイルを確認するには現状restoreで作業ツリーごと戻すしかない。作業ツリーに影響を与えずに過去のファイルを取り出せると、GUIでのプレビュー(絵の確認、音の再生)や「昔の版だけ別フォルダへ書き出す」用途に使える。

## 実装方針

1. `sprout export COMMIT [PATH...] --output DIR`を追加する:
   - `resolve_commit`でコミットを解決し、manifestから対象ファイルを特定する。PATH省略時は全ファイル、ディレクトリ指定は前方一致で展開する(TASK-13の部分復元と同じパス解決ロジックを共有できる)。
   - objectsストアから`--output`で指定したディレクトリへ相対パス構造を保って書き出す。mtime_nsも復元する。
   - 出力先の既存ファイルは上書きしない(`--force`で上書き許可)。出力先がプロジェクト内の場合も、作業ツリーの追跡状態には一切影響を与えない(tracked_pathsを変更しない)。
   - 書き出し前に`hash_file`でオブジェクトの整合性を検証する(既存の`_verify_manifest`相当)。
2. `sprout cat COMMIT PATH`を追加する: 単一ファイルの内容を標準出力へバイナリのまま書き出す(`sys.stdout.buffer`を使用)。GUIやパイプ連携で一時ファイルを作らずに内容を取得できる。
3. どちらも読み取り専用の操作なのでロックは不要。
4. READMEのコマンド一覧に追記する。

## 注意

オブジェクト圧縮(TASK-11)が先に実装されている場合は、伸長処理を共通関数経由で行う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `export`でコミット内の全ファイルまたは指定ファイルを任意のフォルダへ書き出せる
- [ ] #2 exportが作業ツリーと追跡状態に影響を与えない
- [ ] #3 既存ファイルは`--force`なしでは上書きされない
- [ ] #4 `cat`で単一ファイルの内容を標準出力へ取り出せる
- [ ] #5 書き出したファイルのmtimeがコミット時の値に復元される
- [ ] #6 READMEが更新され、export/catの動作がテストで検証されている
<!-- AC:END -->
