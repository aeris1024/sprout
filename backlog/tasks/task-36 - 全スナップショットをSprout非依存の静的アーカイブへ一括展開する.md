---
id: TASK-36
title: 全スナップショットをSprout非依存の静的アーカイブへ一括展開する
status: Done
assignee:
  - '@claude'
created_date: 2026-07-29 19:11
updated_date: '2026-10-29T15:29:00Z'
labels: []
dependencies:
  - TASK-21
  - TASK-22
  - TASK-38
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - README.md
priority: medium
type: feature
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

将来Sproutを使用しなくなった場合でも、.sproutに保存された過去ファイルと履歴情報へアクセスできる退避手段が必要である。現在は単一コミットをexportできるが、分岐や削除済みブランチを含む全スナップショットを、SproutやPythonを必要としない通常のファイル群としてまとめて展開する機能はない。

## ゴール

DBに残る全コミットをコミット日時とコミットIDで識別できるフォルダへ展開し、静的HTMLからコミットの親子関係、メタデータ、メモ、ラベル、ファイル一覧、展開済みファイル、サムネイルへアクセスできるSprout非依存のアーカイブを生成する。

出力物は別環境へコピーした後も、ローカルのWebブラウザとファイルマネージャーだけで閲覧できることを重視する。サーバー、CDN、Sprout固有ランタイムへの依存を持たせない。

## 対象範囲と注意

- 現在のブランチから到達できる履歴だけでなく、削除済みブランチ由来を含むDB上の全コミットを対象とする。
- 日時だけでは同時刻や分岐で衝突するため、各スナップショットの出力名には短縮コミットIDも含める。
- コミット、ファイル、添付、メモ、ラベルの情報はHTMLに加え、機械可読なJSONにも保存する。
- 全previewとその表示順を保存し、HTMLから保存された順序でアクセスできるようにする。添付IDで個々の添付を区別し、元ファイル名が同じ添付も欠落・上書きせずに展開する。
- 通常ファイルへの完全展開では圧縮と重複排除の効果が失われるため、実行前に推定展開容量と出力先の空き容量を確認できるようにする。
- 空ディレクトリ、権限、所有者、シンボリックリンクなど、Sproutが保存していない情報は再現対象外とする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 DBに存在する全コミットが、削除済みブランチ由来の到達不能コミットを含めて漏れなく展開される
- [x] #2 各スナップショットはUTCのコミット日時と短縮コミットIDを含む衝突しないディレクトリ名を持ち、コミット時の相対パス構造とファイル内容が再現される
- [x] #3 生成された静的HTMLで全コミットの親子関係、日時、メッセージ、ID、ブランチ、タグ、メモ、ラベルを確認でき、各スナップショットと展開済みファイルへ相対リンクでアクセスできる
- [x] #4 thumbnailと全previewを、元ファイル名・メディア種別・表示順の情報を維持して書き出し、対応するコミットから保存された順序で閲覧または再生できる
- [x] #5 コミット、ファイル、添付、メモ、ラベルのメタデータが、親ID、パス、サイズ、SHA-256、添付ID、previewの表示順を含むSprout非依存のJSONとして保存される
- [x] #6 HTMLと付随アセットは外部サーバー、CDN、Sprout、Pythonを必要とせず、別の場所へコピーした後もローカルで閲覧できる
- [x] #7 実行前にコミット数、作成予定ファイル数、推定展開容量、出力先の空き容量を確認でき、容量不足を明確に報告する
- [x] #8 既存の空でない出力先を意図せず上書きせず、中断された出力を識別でき、安全に再実行できる
- [x] #9 展開中にオブジェクトの欠落または破損を検出した場合は対象を特定して失敗し、正常完了したように見えるアーカイブを残さない
- [x] #10 コマンドの使用方法、出力構成、容量増加、Sproutが保存していないメタデータの制限がREADMEに記載され、全履歴、分岐、HTML、JSON、添付、複数previewの表示順と同名添付、メモ、ラベル、失敗時の安全性が自動テストで検証される
- [x] #11 アーカイブにrepository_idとrepository_created_atが保存され、別の場所へコピーした後も元リポジトリを一意に識別できる
- [x] #12 元ファイル名が同じ添付が複数あっても添付IDで区別され、アーカイブのファイル・HTML・JSONに欠落や意図しない上書きがない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Repository.plan_archive(output): read all commits (incl. unreachable ones from deleted branches), files, attachments, notes, labels, branches (incl. deleted), tags and repository meta in one read transaction; render every HTML/JSON text in memory; report commit count, file count, estimated bytes and free bytes of the nearest existing ancestor of output.
2. Repository.archive(output): refuse output inside .sprout or non-empty output; build into sibling staging dir '.<name>.sprout-archive-incomplete' containing an INCOMPLETE marker; remove a previous staging dir only when it has the marker; check free space before writing; extract each object once with SHA-256/size verification and copy subsequent duplicates; on any error remove the staging dir and report commit/path/attachment; on success delete marker and rename staging to output.
3. Layout: index.html, archive.json, README.txt at root; snapshots/<UTC yyyymmddThhmmss.ffffffZ>_<id12>/ with index.html, commit.json, files/<commit paths>, attachments/thumbnail/<attachment id>/<name>, attachments/previews/<NNN>_<attachment id>/<name>. Pure HTML+inline CSS, relative URL-encoded links, img/audio/video by media type.
4. CLI 'sprout archive --output DIR [--dry-run] [--json]' with clear insufficient-space error.
5. Tests in tests/test_archive.py covering all ACs; README section on usage, layout, capacity growth, unsupported metadata, safety.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added src/sprout/archive.py (pure HTML/JSON/README rendering, inline CSS, no scripts or external URLs) and Repository.plan_archive/archive plus 'sprout archive --output DIR [--dry-run] [--json]'.
- All commits come from one read transaction over the commits table (not branch reachability), so commits of deleted branches are included; deleted branches are listed with deleted=true.
- Snapshot directories: snapshots/<YYYYMMDDTHHMMSS.ffffffZ>_<12-hex id>; the full ID is used if two short names ever collide. Attachments go to attachments/thumbnail/<id>/<name> and attachments/previews/<NNN>_<id>/<name>; names unusable on Windows are replaced only on disk.
- Estimated size is exact for data files plus the in-memory rendered HTML/JSON (only generated_at may vary). Free space comes from the nearest existing ancestor of the output.
- Output is built in sibling '.<name>.sprout-archive-incomplete' with SPROUT-ARCHIVE-INCOMPLETE.txt, renamed to the output only after every object was verified; on error the staging dir is removed. A rerun removes a staging dir only when it has the marker.
- Each object is decompressed and SHA-256/size-verified once; duplicates are copied from the verified file.
- Windows: staging writes use the \?\ extended-length prefix because snapshot paths exceed MAX_PATH easily (found by a manual run in a deep temp folder; covered by a test).
- Bud (uncommitted) data is intentionally not archived; README says so.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added 'sprout archive --output DIR [--dry-run] [--json]', which expands every commit in the DB (including unreachable commits of deleted branches) into a Sprout-independent static archive: root index.html/archive.json/README.txt and snapshots/<UTC time>_<short id>/ with index.html, commit.json, files/ (original relative paths and mtimes) and attachments/ keyed by attachment ID (previews prefixed by stored order). HTML is plain HTML with inline CSS and relative links (img/audio/video for media); JSON carries repository_id/repository_created_at, parent/children IDs, branches incl. deleted, tags, notes, labels, file path/size/SHA-256 and attachment ID/role/position/name/media type/SHA-256. --dry-run reports commits, files, estimated bytes and free space; insufficient space fails before writing (archive_insufficient_space). Output must be new or empty; work happens in a marked sibling staging dir that is renamed only after all objects verify, is removed on failure (archive_object_invalid names the commit and path or attachment ID), and is replaced on rerun only when marked. Windows long paths handled via the extended-length prefix. README documents usage, layout, size growth and unpreserved metadata. Verification: tests/test_archive.py (8 tests) covers all criteria; full suite 'uv run pytest -q' passes (365 passed, 19 skipped). Not done: commit/merge awaiting user confirmation; buds are intentionally excluded.
<!-- SECTION:FINAL_SUMMARY:END -->
