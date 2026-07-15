---
id: TASK-21
title: コミットにサムネイル(添付メディア)を登録できるようにする
status: To Do
assignee: []
created_date: '2026-07-15 16:26'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: medium
type: feature
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

将来のGUIでコミットツリーに各コミットのサムネイルを表示したい。サムネイルはその場で生成せず、commit時またはcommit後に任意のファイルを登録する方式とする。画像に限定せず、wav等の音声ファイルも添付できるようにする(GUI側で再生・波形表示する想定)。

## 実装方針

### スキーマ

`commit_attachments`テーブルを追加する:

- `commit_id TEXT NOT NULL REFERENCES commits(id) ON DELETE CASCADE`
- `role TEXT NOT NULL DEFAULT 'thumbnail'`(将来の用途拡張のためロール列を持つ。当面はthumbnailのみ)
- `media_type TEXT NOT NULL`(拡張子からのマッピング。png/jpg/webp/gif/wav/mp3等。不明は`application/octet-stream`)
- `object_hash TEXT NOT NULL` / `size INTEGER NOT NULL` / `created_at TEXT NOT NULL`
- `PRIMARY KEY (commit_id, role)`(1コミットにつきロールごと1件)

`CREATE TABLE IF NOT EXISTS`での追加なので既存DBと互換だが、旧バージョンのSproutが新DBを読む事故を防ぐ観点で`SCHEMA_VERSION`を上げるかは実装時に判断する。

### 保存方式

添付ファイルの実体は既存の`_store_object`でobjectsストアに保存し、通常のファイルとdedupを共有する。添付元ファイルはプロジェクト外のパスでも許可する(スクリーンショットフォルダ等から直接登録できると便利)。

### CLI

- `sprout commit -m MSG --thumbnail FILE`: コミット作成と同時に登録
- `sprout thumbnail set COMMIT FILE`: 後付け登録(上書き可)
- `sprout thumbnail remove COMMIT`: 削除
- `sprout thumbnail export COMMIT OUTPUT`: 添付をファイルへ書き出す(GUIやユーザーが内容を取り出す手段)
- `sprout show`にサムネイルの有無・media_type・サイズを表示

サムネイル登録・削除は`@locked`の書き込み操作とする。巨大ファイルの誤登録を防ぐため、サイズ上限(例: 10MB、超過時は警告または拒否)を設ける。

### 他タスクとの関係

TASK-10(gc)が実装済みの場合、参照集合に`commit_attachments.object_hash`を含めるよう更新する。未実装ならTASK-10側の実装時に本テーブルを考慮する。READMEにサムネイルの使い方を追記する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 commit時に`--thumbnail`でサムネイルを登録できる
- [ ] #2 既存コミットへのサムネイルの登録・上書き・削除ができる
- [ ] #3 画像以外のファイル(wav等)も添付でき、media_typeが記録される
- [ ] #4 添付の実体がobjectsストアに保存されdedupされる
- [ ] #5 `thumbnail export`で添付を取り出せる
- [ ] #6 `show`でサムネイルの有無と種別が確認できる
- [ ] #7 gcが存在する場合、添付オブジェクトが削除対象にならない
- [ ] #8 READMEに使い方が記載され、登録・上書き・削除・exportがテストで検証されている
<!-- AC:END -->
