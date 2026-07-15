---
id: TASK-2
title: switch/restoreの未保存変更判定を高速化する
status: To Do
assignee: []
created_date: '2026-07-15 16:14'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
priority: medium
type: enhancement
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 問題

1. `_has_unsaved_changes`は最初に`status()`を呼び変更候補ファイルをハッシュした直後、`_working_content_signature()`で全追跡ファイルをもう一度ハッシュする。大きなバイナリを扱う想定のツールなので、switch/restoreのたびに全ファイルを2回読むコストは体感に直結する。
2. `_is_saved_snapshot`は照合のたびに全コミット×全ファイルのcommit_filesをメモリの辞書へ展開する。履歴が伸びるほどswitch/restoreが線形に遅くなる。

## 修正方針

1. 作業ツリーのsignature(path→(hash, size))を1回だけ計算し、status相当の判定と保存済みスナップショット判定の両方に使い回す。例えば`_working_content_signature`を先に呼び、その結果とhead manifestの比較で変更有無を判定すれば、`status()`によるハッシュ計算を省ける(追跡ファイルが欠けている場合はsignatureがNoneになるので従来どおり「変更あり」として扱う)。
2. `_is_saved_snapshot`はSQLで候補コミットを絞り込む。例: まずファイル数がsignatureと一致するcommit_idをGROUP BY/HAVINGで抽出し、その候補コミットのmanifestだけを読み込んで詳細比較する。signatureに含まれるobject_hash集合を持たないコミットを除外する条件を加えてもよい。

判定結果(どの場合にdiscardが要求されるか)は現状と完全に同一であること。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 未コミット変更の判定時、各追跡ファイルのハッシュ計算が1回で済む
- [ ] #2 `_is_saved_snapshot`が全履歴のcommit_filesを一括でメモリに展開しない
- [ ] #3 discard要否の判定結果が従来と同一である(既存テストが全てパスする)
<!-- AC:END -->
