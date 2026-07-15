---
id: TASK-13
title: restoreで特定のファイルだけを復元できるようにする
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
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

「このファイルだけ昔の版に戻したい」は頻出のユースケースだが、現状の`restore`はスナップショット全体の復元しかできない。

## 実装方針

`sprout restore COMMIT [PATH...]`のようにパス引数を追加する(typerの可変長引数)。

1. パスは`_relative_file`(`must_exist=False`)で正規化し、対象コミットのmanifestに存在するか検証する。存在しなければ`SproutError`。ディレクトリ指定はmanifest内の前方一致(`prefix/`)で展開する。
2. 復元対象を「現在の作業ツリー相当のmanifest + 指定パスだけ対象コミットの状態に置き換えたもの」として構築し、既存の`_materialize`に渡す。こうするとステージング・バックアップ・リカバリの仕組みをそのまま再利用できる。
3. 部分復元では追跡集合(`tracked_paths`)とHEADブランチを変更しない点に注意。`_materialize`は現状`tracked_paths`を全置換するため、部分復元時は指定パスのみ追跡へ追加する形へ`_finalize_materialization`を調整する必要がある。
4. 安全性の判定(`_has_unsaved_changes` / `--discard`)は、指定パスに限定して判定する。指定外のファイルに未保存変更があっても部分復元は妨げない方が使いやすい。ただし復元によって上書きされる指定パス自体に未保存変更があれば従来どおり`--discard`を要求する。
5. 未追跡ファイルとの衝突は従来どおり中止する。

READMEに部分復元の説明を追記する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `restore COMMIT PATH`で指定ファイルのみが復元され、他のファイルは変更されない
- [ ] #2 ディレクトリ指定でその配下の該当ファイルがまとめて復元される
- [ ] #3 指定パスがコミットに存在しない場合は明確なエラーになる
- [ ] #4 指定パスに未保存変更がある場合は`--discard`が要求される
- [ ] #5 HEADブランチと指定外の追跡状態は変化しない
- [ ] #6 READMEに部分復元の使い方が追記されている
- [ ] #7 部分復元・衝突・discard要求がテストで検証されている
<!-- AC:END -->
