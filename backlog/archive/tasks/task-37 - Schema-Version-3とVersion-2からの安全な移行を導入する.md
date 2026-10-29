---
id: TASK-37
title: Schema Version 3へ破壊的に更新する
status: Done
assignee:
  - '@codex'
created_date: '2026-07-29 19:23'
updated_date: '2026-08-08 17:36'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - tests/test_repository.py
  - README.md
priority: medium
type: feature
ordinal: 21500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景 Sproutはまだ実利用されておらず、既存リポジトリとの互換性を維持する必要がない。画像サムネイル、preview、後付けメモ・ラベル、GUI、静的アーカイブに必要な永続データをSchema Version 3として定義する。 ## 保存形式 commit_attachmentsはcommit_id、role、original_name、media_type、object_hash、size、created_at、updated_atを持ち、commit_idとroleを一意とする。commit_notes、commit_labels、repository_id、repository_created_atを追加する。roleとmedia_typeは制限しないTEXTとし、形式やサイズの制約は機能層で定義する。 ## 互換性 Version 2からの移行は実装しない。新規リポジトリはVersion 3で初期化し、異なるスキーマはデータを変更せず拒否する。既存の開発用リポジトリは再初期化する。ユーザー向け操作は後続タスクで実装する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 新規リポジトリがSchema Version 3で初期化され、添付、メモ、ラベル用のテーブルとrepository_id、repository_created_atを持つ
- [x] #2 commit_attachmentsに必要なメタデータを保存でき、コミットとroleの組み合わせが一意である
- [x] #3 roleとmedia_typeは独立したTEXTとして保存され、未知の値や形式別サイズをDB層が拒否しない
- [x] #4 commit_notesはコミットごとに1件、commit_labelsはコミットごとに複数の重複しないラベルを保持できる
- [x] #5 添付、メモ、ラベルは存在するコミットだけを参照し、コミット削除時に外部キー制約で削除される
- [x] #6 ラベル名検索用の索引が含まれる
- [x] #7 repository_idは一意で以後変化せず、repository_created_atは有効なUTC日時である
- [x] #8 Version 2を含む異なるSchema Versionはデータを変更せず安全に拒否され、再初期化が必要と案内される
- [x] #9 新規初期化、制約、メタデータ、外部キー、索引、互換性拒否が自動テストで検証される
- [x] #10 READMEにSchema Version 3の内容と既存開発用リポジトリの再初期化が必要なことを記載する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Schema Version 3のテーブル、外部キー、索引、repository_idとrepository_created_atを定義する。 2. 新規初期化でVersion 3メタデータを生成し、異なるVersionを変更せず拒否する。 3. 制約、任意role/media_type、外部キー削除、ラベル索引、メタデータ不変性をテストする。 4. Version 2を含む非対応スキーマの拒否をテストする。 5. READMEを更新し全テストを実行する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Schema Versionを3へ更新し、commit_attachments、commit_notes、commit_labels、ラベル・添付索引、repository_id、repository_created_atを追加した。check_schemaはVersion 2を含む非対応Versionと不足テーブル・メタデータを自動修復せず拒否し、repository_idとUTC作成日時を検証する。検証結果: 対象テスト4件成功、全テスト106 passed・2 skipped、git diff --check成功。
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @codex
created: 2026-08-08 17:32
---
実利用リポジトリが存在しないため、ユーザー確認によりVersion 2移行を対象外とし、Schema Version 3へ破壊的に更新する方針へ変更した。
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Schema Version 3へ破壊的に更新し、後続の添付・メモ・ラベル・GUI機能に必要な保存領域とリポジトリ識別情報を追加した。旧Versionは再初期化案内付きで変更せず拒否する。全テスト106件成功・2件スキップで検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
