---
id: TASK-62
title: V1の保存構造にブランチID・専用状態テーブル・複数previewの基盤を導入する
status: To Do
assignee: []
created_date: '2026-10-28 16:19'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - gui/src/lib/sprout.ts
  - gui/src/lib/sproutMap.ts
  - tests/test_repository.py
  - tests/test_cli.py
  - tests/test_restore_safety.py
  - README.md
priority: high
type: enhancement
ordinal: 62000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

Sproutはまだ実利用されておらず、既存データとの互換性を維持する前に初期の保存仕様を見直せる。ブランチ名を識別子として使う構造、汎用meta内の現在位置、単一previewを前提とする添付の一意性を整理し、今後の機能追加の基盤を確定する。

## ゴール

Schema Versionは1のまま、ブランチに不変のIDを導入し、コミット・つぼみ・現在位置を名前ではなくIDで関連付ける。ブランチの改名・削除・同名での再作成後も履歴を混同せず、作成時のブランチ名も保持する。

現在のブランチとコミットは専用の状態テーブルへ移す。初回コミット前の現在コミットはNULLで表し、状態の欠落をブランチ先端へのフォールバックで補わない。成功時の状態更新と失敗・中断時の復旧を、既存の操作と一貫させる。

添付ごとに不変のIDを持たせ、1コミットに複数previewとその表示順を保存できるようにする。thumbnailは従来どおり1コミットに1件とし、任意のrole・media_typeを保存できる方針を維持する。IDのNOT NULL、サイズの非負制約、参照整合性などのDB制約を統一する。

つぼみと専用状態テーブルをV1の必須構造とし、起動時の後付け作成や現在位置の互換用フォールバックを整理する。変更前の開発用DBは自動変換・修復せず、変更せずに拒否して再初期化を案内する。

## 対象範囲

保存構造と既存操作の対応、CLI・JSON・GUIの型、芽のマップの識別、テスト、README更新を含める。previewの追加・置換・削除・取得・並べ替えの操作機能はTASK-38で扱う。

既存データの移行処理、更新日時の保存仕様変更、file_id、共通manifest、代表previewの指定は含めない。GUIでpreviewを管理する共通機能の新規タスクも本件では作成しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 新規リポジトリがSchema Version 1のまま、ブランチID・専用状態テーブル・複数previewと表示順・統一したDB制約を持つ初期仕様で作成される
- [ ] #2 ブランチに不変のIDがあり、コミット・つぼみ・現在位置がIDで関連付く。改名・削除・同名再作成後も枝を混同せず、作成時のブランチ名と削除済みの枝の識別を保持する
- [ ] #3 現在のブランチとコミットを専用状態テーブルで参照整合性を保って記録し、初回コミット前は現在コミットをNULLとする。状態の欠落や不正な参照を先端へのフォールバックで補わない
- [ ] #4 commit・全体restore・switch・branch --switch・go・つぼみ復元で現在位置が一貫して更新され、部分restore・失敗・中断後の復旧でも正しい状態が保たれる
- [ ] #5 各添付に不変のIDがあり、1コミットに複数previewとその表示順を保存できる。IDと表示順は再オープン後も保持され、thumbnailは1コミットに1件だけ保存できる
- [ ] #6 IDのNOT NULL、ファイルサイズの非負制約、参照先の存在と削除時の整合性などのDB制約が通常ファイル・つぼみ・添付・状態を通じて統一され、任意のrole・media_typeは保存できる
- [ ] #7 つぼみと専用状態テーブルがV1の必須構造として検証され、起動時に不足構造を後付け作成しない。変更前の開発用DBや必須構造の欠落はデータを変更せず拒否し、再初期化を案内する
- [ ] #8 CLI・JSONで必要なブランチID・添付ID・表示順を確認でき、GUIの型と芽のマップがブランチIDで同一性を扱う。既存の名前によるCLI操作と履歴表示を維持する
- [ ] #9 既存の復元・つぼみ・thumbnail・メモ・ラベル・タグ・gc・doctor・stats・pruneなどが新しい保存構造で動作し、参照中の履歴とオブジェクトを保護する
- [ ] #10 ブランチの改名・削除・同名再作成、初回コミット前、状態更新と中断復旧、複数previewと再オープン時の表示順、thumbnailの一意性、不正値拒否、CLI・JSON・GUIの対応が自動テストで検証される
- [ ] #11 READMEに新しいV1の初期仕様と変更前の開発用DBの再初期化方針が記載され、既存データの移行処理は追加されない
<!-- AC:END -->
