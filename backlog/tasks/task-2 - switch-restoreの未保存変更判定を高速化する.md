---
id: TASK-2
title: switch/restoreの未保存変更判定を高速化する
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-15 16:14'
updated_date: '2026-07-20 09:45'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
modified_files:
  - src/sprout/repository.py
  - tests/test_repository.py
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
- [x] #1 未コミット変更の判定時、各追跡ファイルのハッシュ計算が1回で済む
- [x] #2 `_is_saved_snapshot`が全履歴のcommit_filesを一括でメモリに展開しない
- [x] #3 discard要否の判定結果が従来と同一である(既存テストが全てパスする)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. `_has_unsaved_changes` で追跡ファイルのハッシュを1回だけ計算し、その結果で status 相当の変更有無を判定する（status() の二重ハッシュをやめる）
2. 欠けている追跡ファイルなど、既存の discard 判定セマンティクスは維持する
3. `_is_saved_snapshot` はファイル数一致の候補コミットだけを SQL で絞り込み、その manifest だけを比較する
4. ハッシュ回数・全件展開しないこと・既存 discard 挙動をテストで検証する
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
実装: `_has_unsaved_changes` が追跡ファイルを1回だけハッシュし status 相当判定と snapshot 判定に再利用。`_is_saved_snapshot` は COUNT 一致の候補のみ SQL で絞り込み。
検証: pytest → 50 passed, 2 skipped。
- AC1: test_has_unsaved_changes_hashes_each_tracked_file_once
- AC2: test_is_saved_snapshot_does_not_load_all_commit_files
- AC3: 既存 discard/switch/restore 系を含む全テスト通過
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
switch/restore の未保存変更判定で追跡ファイルの二重ハッシュをやめ、保存済みスナップショット照合も候補コミットのみ読むようにした。discard 要否は従来どおり。pytest 50 passed / 2 skipped で AC1–3 を確認。
<!-- SECTION:FINAL_SUMMARY:END -->
