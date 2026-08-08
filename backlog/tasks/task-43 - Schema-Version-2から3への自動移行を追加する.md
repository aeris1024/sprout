---
id: TASK-43
title: Schema Version 2から3への自動移行を追加する
status: Done
assignee:
  - '@codex'
created_date: '2026-08-08 19:29'
updated_date: '2026-08-08 19:38'
labels: []
dependencies:
  - TASK-37
references:
  - src/sprout/repository.py
  - tests/test_repository.py
  - README.md
priority: medium
type: enhancement
ordinal: 43000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Schema Version 2の既存リポジトリを、履歴とobjectsを失わずSchema Version 3へ自動変換する。最初のRepository.discover時に有効なv2だけを対象として安全に移行し、TASK-37で採用した再初期化必須の方針を後続要求として置き換える。v1、将来版、壊れたv2は変更せず拒否する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 有効なSchema Version 2リポジトリが最初のRepository.discover時に自動でVersion 3へ移行する
- [x] #2 コミット、ファイル、ブランチ、タグ、追跡状態、objectsの内容が移行前後で保持される
- [x] #3 Version 3の添付、メモ、ラベル用テーブルと索引が追加され、既存コミットを参照できる
- [x] #4 移行時に新しいrepository_idを生成して以後固定し、repository_created_atは最古コミット日時、空リポジトリでは移行日時になる
- [x] #5 変換前にSQLite backup APIで.sprout/backups配下へ一意なVersion 2データベースバックアップを作成する
- [x] #6 移行はリポジトリロックと単一トランザクションで行い、schema_versionを最後に更新し、失敗時はVersion 2のままロールバックする
- [x] #7 同時実行を拒否し、移行後の再discoverでは再変換やメタデータ変更を行わない
- [x] #8 Version 1、将来Version、必須構造が壊れたVersion 2はデータを変更せず明確なエラーで拒否する
- [x] #9 実際のVersion 2構造から作るフィクスチャで成功、保持、バックアップ、失敗、冪等性をテストし、READMEに自動移行と復旧方法を記載する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 実物のVersion 2スキーマを定数化し、必須テーブル・列・メタデータ・圧縮形式を変更前に検証する。 2. リポジトリロック下でSQLite backup APIによる一意なバックアップを作成する。 3. ロック取得後にVersionを再確認し、単一トランザクションでVersion 3のテーブル・索引・repository_id・repository_created_atを追加してschema_versionを最後に更新する。 4. discoverへ自動移行を統合し、移行後検証、冪等性、旧版・将来版・壊れたVersion 2の非変更拒否を実装する。 5. 実物Version 2フィクスチャでデータ／objects保持、バックアップ、日時導出、ロック、失敗ロールバックを検証し、README更新後に全テストを実行する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Repository.discoverへVersion 2検出と自動移行を追加した。有効なv2構造・列・メタデータ・圧縮・DB/FK整合性を変更前に検査し、ロック下でSQLite backup APIによる検証済みバックアップを作成後、単一トランザクションでv3要素とメタデータを追加する。最古コミット日時または移行日時をrepository_created_atに採用し、version更新は最後に行う。検証: v2移行対象7テスト成功、全テスト129 passed・2 skipped、追加の移行後注記／ラベル／サムネイルテスト成功、git diff --check成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Schema Version 2を初回discover時に履歴とobjectsを保持してVersion 3へ自動移行する機能を実装した。検証済みSQLiteバックアップ、事前構造検査、ロック、原子的ロールバック、冪等性、旧版／将来版／破損拒否、READMEの復旧手順を含み、全129テスト成功で確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
