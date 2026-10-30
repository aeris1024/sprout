---
id: TASK-81
title: ファイルの更新日時をコミットごとの各パスに保存する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-29T19:07:00Z'
updated_date: '2026-10-30 14:43'
labels: []
dependencies:
  - TASK-80
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - src/sprout/archive.py
  - tests/test_repository.py
  - tests/test_restore_safety.py
  - tests/test_archive.py
  - README.md
priority: high
type: enhancement
ordinal: 80000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現行V1は同じ内容が最初にコミットされた更新日時をobjects.file_mtime_nsに1件だけ保存し、内容が同じ別ファイルや別コミットでも共有する。このため内容が同じで更新日時が異なるファイルを保存時点どおりに復元できない。つぼみは既に各パスの日時を持っている。内容の重複排除を維持したまま、通常コミットも各保存時点・各パスの更新日時を保持する仕様へ変更する。これは現在の明示的仕様の変更であり、日時だけ異なる場合の変更判定も一貫させる。非互換形式の扱いはTASK-80に従い、旧開発用DBの移行は本件に含めない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 同じ内容でもパスやコミットが異なれば、それぞれ保存時点のmtime_nsを保持できる。objectsの内容データの重複排除は維持する
- [x] #2 全体復元・部分復元・ブランチ切り替え・go・export・全履歴archiveが、そのコミットの各パスに保存した更新日時を用いる。つぼみ保存・復元の個別更新日時も維持する
- [x] #3 更新日時だけが変化した場合のstatus・diff・log・commitの扱いを明文化し、同じ方針で動作させる。保存済み日時と作業ツリーの日時が異なるだけで予期しない未保存変更や復元拒否を生じさせない
- [x] #4 show・JSON・GUIが必要な更新日時を各コミットの各パスから取得し、オブジェクト単位の初回日時に依存しない。異常な日時や欠落は定義した制約・検査で検出する
- [x] #5 ファイルシステムの時刻精度を考慮し、同内容の複数パス・別コミット、日時のみの変更、部分復元の選択外維持、復元失敗・中断復旧、export/archive、重複排除を自動テストで検証する
- [x] #6 新しい保存構造はTASK-80の形式番号・互換性方針に従い、READMEに更新日時の仕様と開発用DBの扱いを記載する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Use schema V4 because historical development formats already used 2 and 3. Store a required signed integer mtime_ns per commit/path, remove object-level file time, preserve content deduplication and existing content-only change detection. Route manifests and archives through per-snapshot times; validate corrupted times. Preserve immutable V1 SQL fixture and freeze V4 definition; reject older formats without migration. Document semantics and source/destination filesystem precision. Verify restore/partial/switch/go/bud/export/archive/JSON, failure recovery, metadata constraints, CLI/GUI regressions and all Python tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented commit_files.mtime_ns and removed objects.file_mtime_ns. Manifests, show/JSON, restoration and archive now use per-path snapshot values. Timestamp-only differences stay clean and cannot create commits/buds; a content/path commit captures actual times for all files. Archive also preserves epoch zero. Invalid noninteger values are constrained, rejected by reads and diagnosed by doctor. V4 avoids reusing historical development numbers 2/3; V1 fixture and V4 definition have frozen checks. Added 15 timestamp tests covering deduplication, separate commits, all restore paths, partial scope, buds, export/archive/JSON, OSError rollback, interrupted recovery and filesystem precision. Final verification: Python full suite 456 passed and 19 skipped (169.54s); GUI App/SnapshotFiles/ComparePanel/CLI tests 74 passed; TypeScript noEmit and git diff --check passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Preserve each committed path modification time independently of content deduplication, using schema V4. Keep timestamp-only change detection compatible, validate saved times and preserve epoch zero in archives. Document old DB backup/reinitialization and test per-path/per-commit restoration, JSON, archives and recovery. Verified full Python suite (456 passed, 19 skipped), 74 GUI tests and TypeScript checks.
<!-- SECTION:FINAL_SUMMARY:END -->
