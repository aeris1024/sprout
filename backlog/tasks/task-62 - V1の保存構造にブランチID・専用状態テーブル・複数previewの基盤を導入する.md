---
id: TASK-62
title: V1の保存構造にブランチID・専用状態テーブル・複数previewの基盤を導入する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-28 16:19'
updated_date: '2026-10-28 16:46'
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
- [x] #1 新規リポジトリがSchema Version 1のまま、ブランチID・専用状態テーブル・複数previewと表示順・統一したDB制約を持つ初期仕様で作成される
- [x] #2 ブランチに不変のIDがあり、コミット・つぼみ・現在位置がIDで関連付く。改名・削除・同名再作成後も枝を混同せず、作成時のブランチ名と削除済みの枝の識別を保持する
- [x] #3 現在のブランチとコミットを専用状態テーブルで参照整合性を保って記録し、初回コミット前は現在コミットをNULLとする。状態の欠落や不正な参照を先端へのフォールバックで補わない
- [x] #4 commit・全体restore・switch・branch --switch・go・つぼみ復元で現在位置が一貫して更新され、部分restore・失敗・中断後の復旧でも正しい状態が保たれる
- [x] #5 各添付に不変のIDがあり、1コミットに複数previewとその表示順を保存できる。IDと表示順は再オープン後も保持され、thumbnailは1コミットに1件だけ保存できる
- [x] #6 IDのNOT NULL、ファイルサイズの非負制約、参照先の存在と削除時の整合性などのDB制約が通常ファイル・つぼみ・添付・状態を通じて統一され、任意のrole・media_typeは保存できる
- [x] #7 つぼみと専用状態テーブルがV1の必須構造として検証され、起動時に不足構造を後付け作成しない。変更前の開発用DBや必須構造の欠落はデータを変更せず拒否し、再初期化を案内する
- [x] #8 CLI・JSONで必要なブランチID・添付ID・表示順を確認でき、GUIの型と芽のマップがブランチIDで同一性を扱う。既存の名前によるCLI操作と履歴表示を維持する
- [x] #9 既存の復元・つぼみ・thumbnail・メモ・ラベル・タグ・gc・doctor・stats・pruneなどが新しい保存構造で動作し、参照中の履歴とオブジェクトを保護する
- [x] #10 ブランチの改名・削除・同名再作成、初回コミット前、状態更新と中断復旧、複数previewと再オープン時の表示順、thumbnailの一意性、不正値拒否、CLI・JSON・GUIの対応が自動テストで検証される
- [x] #11 READMEに新しいV1の初期仕様と変更前の開発用DBの再初期化方針が記載され、既存データの移行処理は追加されない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 最新origin/mainを基準とする専用ブランチで、TASK-62の保存構造と既存操作の対応だけを実装する。Schema Versionは1を維持し、既存開発用DBの移行処理は作らない。TASK-38のpreview操作コマンドは実装しない。
2. branchesに不変のIDを導入し、コミット・つぼみ・現在のブランチをIDで関連付ける。作成時のブランチ名は履歴表示用に保持する。削除済みの枝は識別用の記録を残し、有効なブランチ一覧・名前の一意性・先端の保護対象から外す。同名での再作成には新しいIDを割り当てる。削除済みの枝のつぼみを復元する場合は、現行動作に合わせ現在の有効ブランチを維持し、同名の別枝には接続しない。
3. 必ず1行あるrepository_stateにhead_branch_idとcurrent_commit_idを外部キー付きで保存する。初回コミット前のcurrent_commit_idはNULLとし、値の欠落は不正なDBとして拒否する。復元APIでは現在位置の更新省略とNULLへの更新を区別する。active_operationは既存の復旧記録とともに維持し、成功時の現在位置・追跡状態・操作完了を同じDBトランザクションで確定する。
4. 添付に不変のIDと非負の表示順を持たせ、1コミットに複数previewを保存可能にする。thumbnailだけはコミットごとに1件とし、置き換え時もIDを維持する。未知のrole・media_typeは許可する。IDのNOT NULL・サイズの非負制約・外部キー・削除時の整合性を統一する。
5. 必須テーブル・列・制約・専用状態を読み取り専用で検査し、変更前のV1と不完全なDBを変更せずに拒否する。起動時のつぼみテーブルの後付け作成と現在位置のフォールバックを削除する。
6. CLI・JSONへ必要なブランチID・添付ID・表示順を追加し、showとtreeから添付一覧を取得可能にする。既存のthumbnailフィールドと名前によるCLI操作を維持する。GUIの型・芽のマップをIDに基づく関連付けへ更新し、改名や同名再作成で枝を混同しないようにする。
7. 新規初期化、改名・削除・同名再作成とつぼみ復元、初回コミット前の状態、各操作の成功・失敗・中断復旧、複数previewの順序保持、thumbnailの一意性、DB制約と旧V1の非変更拒否を検証する。Python全テスト、GUIテストとビルド、CLI/JSONの一連操作、差分チェックを行い、READMEの初期仕様と再初期化案内を更新する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 実装

ブランチに不変のIDを導入し、コミット・つぼみ・専用のrepository_stateから外部キーで参照する。ブランチ削除は識別用の記録を残して先端を解除し、有効な名前だけを一意にする。改名後のつぼみ復元は同じIDの現在名を使い、削除済みの枝のつぼみは同名で再作成した別枝へ接続しない。

現在位置の更新省略とNULLへの更新を区別し、初回コミット前のつぼみを復元した場合もNULLを保持する。その状態からの保存は既存の枝先を動かさず、新しい枝を作る。復元の確定状態を明示的に記録し、同じ現在位置への移動でも確定後のエラー・中断で退避つぼみを削除しない。確定前の中断では既存の復旧記録で巻き戻す。

添付に不変のIDと整数の表示順positionを導入し、複数previewを保存・再取得できる。thumbnailは部分一意索引で1件に制限し、置き換えでもIDを保持する。IDのNOT NULL、サイズ・表示順の非負整数制約、参照整合性を統一した。

新しいV1のテーブル・索引・制約と状態を読み取り専用で検査し、以前のV1と不完全なDBを変更せず拒否する。つぼみテーブルの後付け作成と現在位置のフォールバックは削除した。CLI・JSON・GUIの型と芽のマップをIDに対応させ、showに添付一覧を追加した。ブランチ一覧の名前・ID・現在の選択は1つのSQLスナップショットで取得する。READMEに新仕様と再初期化方針を記載した。

## 検証

- Python全体: .venv/Scripts/python.exe -m pytest -q -rs -p no:cacheprovider --tb=short --basetemp .test-tmp/task62-final は286 passed, 19 skipped。18件はWindowsのsymlink作成権限、1件は非Windows向け大小文字判定。Windows junctionの保護テストは成功。
- 最後のブランチ参照取得の調整後: tests/test_repository.py・tests/test_cli.py・tests/test_v1_storage.py は215 passed, 2 skipped。
- 新仕様の回帰テスト20件には改名・削除・同名再作成、初回コミット前の状態、不完全なV1の非変更拒否、複数previewと順序、thumbnailのID保持と一意性、不正値拒否、復元確定後のOSError・KeyboardInterrupt時の退避保持を含む。
- GUI: vitest runは38 passed。tscとvite buildも成功。改名・同名再作成・削除済みの枝をIDで区別するマップのテストを追加。
- 別プロセスのCLI/JSONでinit・track・thumbnail付きcommit・改名と名前再利用・go・bud復元・状態・note・label・show・export・doctor・stats・gc/prune dry-runを検証。実際の変更前V1を旧コードで生成し、新CLIがDB本体を変更せず構造化エラーで拒否することも確認した。
- git diff --checkとPython構文チェック成功。

previewの操作コマンドはTASK-38に残し、更新日時の仕様・file_id・共通manifest・代表previewは変更していない。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
V1の初期保存構造をブランチID・専用状態テーブル・統一したDB制約・複数previewのIDと表示順へ更新した。CLI・JSON・GUIと復旧処理を対応させ、変更前V1は非変更で拒否する。Python全体286件成功・19件環境条件スキップ、最終調整後の関連215件成功、GUI38件成功、型チェック・ビルド・別プロセスCLI/JSON・差分チェックで確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
