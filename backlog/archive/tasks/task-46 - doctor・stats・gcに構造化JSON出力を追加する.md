---
id: TASK-46
title: doctor・stats・gcに構造化JSON出力を追加する
status: Done
assignee:
  - '@claude'
created_date: 2026-08-09 08:34
updated_date: '2026-10-29T15:18:00Z'
labels: []
dependencies:
  - TASK-45
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - tests/test_cli.py
  - README.md
priority: medium
type: enhancement
ordinal: 46000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Agentやスクリプトがリポジトリ診断・容量統計・GC候補を安定して解析できるよう、doctor、stats、gcに--jsonを追加する。既存の人向け出力と処理内容は維持し、doctorの正常・異常、statsの各容量指標、gcのdry-run・実処理結果を明示的なフィールドで返す。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 doctor --jsonが正常状態、検査オブジェクト数、問題の種類と詳細を有効なJSONで返し、問題検出時の終了コード1を維持する
- [x] #2 stats --jsonがコミット数、ブランチ数、追跡パス数、オブジェクト数と容量、論理容量、ユニーク容量、重複排除量を有効なJSONで返す
- [x] #3 gc --jsonとgc --dry-run --jsonが対象オブジェクト・一時ファイル、件数、解放容量、dry-runか実処理かを有効なJSONで返す
- [x] #4 --jsonを指定しない既存の人向け出力と各コマンドの変更・非変更動作が維持される
- [x] #5 リポジトリ検出や処理エラーが--json指定時に構造化エラーとして返る
- [x] #6 正常系・異常系・dry-run・実処理のCLIテストとREADMEの使用例が追加される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. cli.pyのdoctor・stats・gcに--jsonを追加する。repositoryの結果（DoctorResult・RepoStats・GcResult）をそのままフィールドに写し、処理内容は変えない。
2. doctor --jsonは問題があっても結果JSONをstdoutへ出し、終了コード1を維持する（serveでもresultとexit_codeが返る）。
3. エラーは既存のmain()の構造化エラー処理（--json検出）に任せる。
4. CLIテスト（正常・異常・dry-run・実処理・リポジトリ外エラー）とREADMEのJSONスキーマを追加する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- doctor・stats・gcの--jsonは、repositoryの結果をそのままフィールドに写した。処理内容と人向け出力は変更していない。
- doctor --jsonは、問題があっても結果JSONをstdoutへ出して終了コード1を返す（stderrは空）。serveでもresultとexit_codeが返る。
- エラーは既存のmain()の構造化エラー処理を利用（リポジトリ外ではsprout_error）。
- 検証: tests/test_cli.pyに7件追加（doctor正常・異常、stats、gc dry-run・実処理、4コマンドのリポジトリ外エラー）。pytest全体は364 passed / 19 skipped。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
doctor・stats・gcに--jsonを追加した。doctorはok・checked_objects・issues（kind・detail）を返し、問題検出時も結果JSONを出して終了コード1を維持する。statsは件数と各容量（objects_bytes・logical_bytes・unique_bytes・dedup_saved_bytes）、gcはdry_run・件数・解放容量・対象オブジェクトと一時ファイルを返す。エラーは既存の構造化エラー形式で返る。--jsonなしの出力と動作は変えていない。CLIテスト7件とREADMEのスキーマ・使用例を追加し、pytestは364 passed / 19 skipped。
<!-- SECTION:FINAL_SUMMARY:END -->
