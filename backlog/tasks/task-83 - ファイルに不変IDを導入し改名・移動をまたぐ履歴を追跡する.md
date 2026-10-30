---
id: TASK-83
title: ファイルに不変IDを導入し改名・移動をまたぐ履歴を追跡する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-29T20:08:00Z'
updated_date: '2026-10-30 15:43'
labels: []
dependencies:
  - TASK-80
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - tests/test_repository.py
  - tests/test_restore_safety.py
  - tests/test_v1_storage.py
  - README.md
priority: high
type: feature
ordinal: 82000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在は通常ファイルをコミットとパスで識別しており、素材の改名・移動後に同じ素材の履歴を追うための不変の識別子がない。未運用の段階でファイルの同一性の規則を決め、将来の素材別履歴やpreviewとの関連付けに利用できるようにする。内容のハッシュは重複排除の識別子として維持し、素材の同一性とは分離する。外部アプリの改名を内容一致だけで自動確定する仕組み、複数親のマージ機能、previewとの関連付けそのものは本件に含めない。保存形式の変更はTASK-80に従う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 追跡ファイルにパスや内容から独立した不変のfile_idがあり、コミットやつぼみの各保存時点におけるパス・内容との関係を保持できる
- [x] #2 明示的な改名・移動ではIDを維持し、コピーや新規ファイルには別IDを割り当てる。同じ内容の別ファイルをハッシュだけで同一素材にしない。追跡解除・再登録・削除後の同名作成・外部での改名の扱いを文書化する
- [x] #3 ブランチの分岐・切り替え・過去版の全体/部分復元・つぼみ復元でも保存された素材の同一性を保持し、パスやIDが衝突する場合は既存データを無断で統合・上書きしない
- [x] #4 CLI・JSONから改名・移動をまたぐ同一素材の履歴と各時点のパスを確認できる。既存のパス指定履歴との使い分けが明確で、GUIが同一性を識別できる
- [x] #5 ファイルIDを導入しても内容の重複排除を維持し、show・export・archiveなどの読み取り、prune・gc・doctorなどの保護と整合性検査が成立する。削除/取り消し機能とのID復旧規則も定義する
- [x] #6 改名・移動・コピー・同内容の別素材・同名再作成・枝の分岐・部分復元・つぼみ・衝突と失敗を自動テストで検証し、形式番号と互換性の方針およびREADMEを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Review proposal: schema V6 with UUID file identity independent of path/hash, carried by tracking bindings, commits and buds. Explicit Sprout moves preserve IDs; copies/new registrations receive new IDs. Untrack/retrack and re-registration after a committed deletion create new IDs. While tracking remains continuous, same-path replacements retain identity (including atomic saves); do not infer external renames or recreation from hashes or filesystem inode changes. Full restores recover snapshot bindings; partial restores reject identity collisions with other or differently bound paths. Add file-ID history CLI/JSON, keep path history semantics, and integrate archive, gc/doctor, trash and failure recovery. Preserve frozen V5 and reject older DBs. After approval, implement/test/finalize this task before TASK-84 and TASK-85; each task gets its own branch, commit, ff-only main integration and push.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User approved the combined TASK-83 through TASK-85 policy. Proceed continuously with independent validation and integration per task.

Implemented schema V6 file_identities and UUID bindings for tracked paths, commit files and bud files. Moves preserve identity; copy/re-registration creates new IDs. Snapshot restore recovers IDs and partial restores reject conflicts without replacing unselected bindings. Added file-history CLI/JSON and file IDs in show/bud/archive and GUI files. Identity-aware status/commit/buds/saved-snapshot and prune protection retain content deduplication. Frozen V5 fixture and compatibility rejection added. Validation: full run 488 passed, 19 skipped and one old raw-SQL fixture missing required ID; fixed fixture and its rerun passed. Added identity/prune case and all 6 identity tests passed; 14 prune/saved-snapshot checks and 4 materialization checks passed after final changes. Final coverage totals 490 passed/19 skipped across full and focused runs; GUI full 107 passed, TypeScript noEmit and diff check passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Introduce immutable file identities through tracking, moves, snapshots, buds, restoration and trash. Expose cross-path history and IDs through CLI/JSON/GUI/archive; reject partial identity collisions and protect restored identities from prune. Use schema V6 with explicit old-format rejection. Verified full regression coverage plus focused identity/prune/materialization tests and 107 GUI tests.
<!-- SECTION:FINAL_SUMMARY:END -->
