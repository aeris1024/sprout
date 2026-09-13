---
id: TASK-50
title: 現行の保存形式をVersion 1に統合して旧形式の互換処理を削除する
status: Done
assignee:
  - '@codex'
created_date: '2026-09-13 10:25'
updated_date: '2026-09-13 10:32'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - tests/test_repository.py
  - tests/test_restore_safety.py
  - README.md
priority: medium
type: chore
ordinal: 50000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
正式リリース前の整理として、現行機能を維持したままDBスキーマと復旧記録を新しいVersion 1へ統合する。既存の開発用リポジトリは手動で再初期化する前提で、旧形式の変換は提供しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 新規DBが現行の全テーブル・索引・制約・メタデータとZstandard保存を持つVersion 1として初期化され、再オープンで識別情報が変わらない
- [x] #2 DBのv2からv3への移行・専用バックアップ・旧形式定数が削除され、旧v1・v2・v3・未知版・必須構造の欠落をデータ変更なしで拒否する
- [x] #3 復旧記録の現行構造がVersion 1になり、旧形式変換を削除し、非対応記録と作業ファイル・復旧バックアップを保持して拒否する
- [x] #4 現行形式のロールバック・中断復旧・再中断・未保存ファイル保護・パス保護が動作する
- [x] #5 READMEが再初期化と正式リリース前の互換性非保証を説明し、CLI・JSON契約とアプリ版0.1.0を維持する
- [x] #6 移行テストと旧形式に依存する通常復旧テストを整理し、Python全テストと新規リポジトリのCLI・JSON操作を検証する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. ユーザー承認済み計画に従い最新origin/mainを基準に現行DBをVersion 1へ統合し、移行処理を削除する。2. 復旧記録をVersion 1に統一し旧形式変換を削除する。3. 非対応DBと復旧記録の非変更拒否、現行復旧動作のテストを更新する。4. READMEの再初期化方針とリリース前の互換性方針を更新する。5. Python全テストと新規リポジトリのCLI・JSON操作を検証し、差分をレビューする。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
現行DBをVersion 1に統合し、v2からv3への移行・専用バックアップ・ensure_schemaと旧復旧記録変換を削除した。check_schemaはmode=roで開きジャーナルモードを変更せず、必須テーブルとメタデータも検証する。SQLiteが読み取り時に作る空WAL/SHMを除き、DB本体・WALデータ・objects・作業ファイルが保持されることを検証した。現行復旧形式は整数Version 1とし、非対応版・版なし・不正型を拒否する。既存の通常復旧とパス保護テストを現行記録へ更新した。

検証: uv --cache-dir .uv-cache run --frozen pytest -q -rs --basetemp .test-tmp/task50-final は220 passed, 19 skipped。スキップはWindowsのsymlink作成権限18件と非Windows向け大小文字判定1件。別プロセスCLI/JSONでinit・track・サムネイル付きcommit・note・label・branch・show・status・log・tree・restore・switch・旧v3拒否を確認した。git diff --check成功。GUI/CLIのコードとアプリ版0.1.0、既存未追跡ファイルは変更していない。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
現行DBと復旧記録を新しいVersion 1へ統合し、旧形式の移行コードを削除した。旧DBと非対応復旧記録を保持して拒否し、READMEを手動再初期化と正式リリース前の互換性非保証へ更新した。全テスト220件成功・環境条件19件スキップ、別プロセスCLI/JSON検証と差分チェックで確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
