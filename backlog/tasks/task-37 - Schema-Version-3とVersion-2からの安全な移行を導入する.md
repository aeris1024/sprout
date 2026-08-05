---
id: TASK-37
title: Schema Version 3とVersion 2からの安全な移行を導入する
status: To Do
assignee: []
created_date: '2026-07-29 19:23'
updated_date: '2026-07-29 19:46'
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
## 背景

現在のSproutはSchema Version 2で、Zstandard圧縮されたオブジェクトと基本的なコミット履歴を管理している。今後の画像サムネイル、クリック表示用preview、後付けメモ・ラベル、GUI、静的アーカイブに必要な永続データを追加するにあたり、個別機能ごとに場当たり的なスキーマ変更を行わず、Schema Version 3として一度に定義したい。

また、現在は期待するSchema Versionと一致しないリポジトリを拒否するだけである。既存のVersion 2リポジトリを失わずにVersion 3へ移行できる正式な経路が必要である。

## Schema Version 3に含めるデータ

- コミット添付: commit_id、role、original_name、media_type、object_hash、size、created_at、updated_at
- コミットメモ: commit_id、note、updated_at
- コミットラベル: commit_id、label
- meta: リポジトリを一意に識別するrepository_id
- meta: リポジトリの作成日時を示すrepository_created_at

roleはファイル形式ではなく用途を表す。初期の代表値は、ツリーへ常時表示するサイズ制限付き静止画像のthumbnailと、コミット選択時に開く任意形式ファイルのpreviewとする。media_typeは実際のファイル形式を表す。roleとmedia_typeは将来追加できるTEXTとして保持し、DB層では特定のファイル形式やサイズを固定しない。形式とサイズの制約は各roleを操作する機能層で定義する。

添付、メモ、ラベルを操作するユーザー向け機能はそれぞれ後続タスクで実装する。本タスクはVersion 3の保存形式、初期化、Version 2からの安全な移行、互換性検査を責務とする。

## 移行方針

Version 2の既存データ、参照、オブジェクトを保持したままVersion 3へ移行できること。移行が中断または失敗した場合に、Schema Versionだけが進んだり一部のテーブルだけが残ったりせず、再試行可能であることを重視する。Version 1以前は今回の直接移行対象に含めない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 新規リポジトリがSchema Version 3で初期化され、添付、メモ、ラベル用のテーブルとrepository_id、repository_created_atを持つ
- [ ] #2 commit_attachmentsに元ファイル名、メディア種別、オブジェクトハッシュ、サイズ、作成日時、更新日時を保存でき、コミットとroleの組み合わせが一意である
- [ ] #3 roleは用途、media_typeは形式として独立して保存され、未知のroleとmedia_typeをDB層が拒否しない
- [ ] #4 DBスキーマは添付ファイルの形式やサイズを固定せず、thumbnail等の制約を機能層で定義できる
- [ ] #5 commit_notesはコミットごとに1件の編集可能なメモを保持でき、commit_labelsはコミットごとに複数の重複しないラベルを保持できる
- [ ] #6 既存のSchema Version 2リポジトリを、コミット、ファイル、ブランチ、タグ、追跡状態、オブジェクトを失わずにVersion 3へ移行できる
- [ ] #7 移行の失敗または中断によって半端なVersion 3状態にならず、Version 2のデータを保持して安全に再試行できる
- [ ] #8 移行後のrepository_idは一意で以後変化せず、repository_created_atは有効なUTC日時として保持される
- [ ] #9 Version 2を通常操作で開いた場合は必要な移行方法が明確に案内され、未知または未対応のSchema Versionは安全に拒否される
- [ ] #10 Version 3をVersion 2対応の旧Sproutが誤って更新できないよう、Schema Versionによる互換性境界が維持される
- [ ] #11 添付、メモ、ラベルは存在するコミットだけを参照し、コミット削除時には関連レコードが外部キー制約に従って削除される
- [ ] #12 ラベル名による履歴検索を全コミット走査に依存せず行える索引が含まれる
- [ ] #13 新規初期化、Version 2移行、データ保持、失敗時ロールバック、再試行、互換性拒否が自動テストで検証され、READMEに移行方法とバックアップ上の注意が記載される
<!-- AC:END -->
