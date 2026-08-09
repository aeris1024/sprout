---
id: TASK-45
title: doctorのコンソール終了コードを修正する
status: Done
assignee:
  - '@codex'
created_date: '2026-08-09 08:18'
updated_date: '2026-08-09 08:25'
labels: []
dependencies: []
references:
  - src/sprout/cli.py
  - tests/test_cli.py
modified_files:
  - src/sprout/cli.py
  - tests/test_cli.py
priority: high
type: bug
ordinal: 45000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
doctorが整合性問題を検出して表示しても、実際のsproutコンソールエントリーポイントが終了コード0を返すため、自動診断が正常と誤認する。問題検出時はプロセス終了コード1、正常時は0を返すよう修正し、エントリーポイント経由の回帰テストを追加する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 正常なリポジトリでsprout doctorが終了コード0を返す
- [x] #2 欠損または破損オブジェクトを検出したsprout doctorが問題を報告して終了コード1を返す
- [x] #3 コンソールエントリーポイント相当のmain関数を通すテストが終了コード伝播を検証する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. mainがTyper appの整数戻り値をプロセス終了コードとして伝播するよう修正する。 2. 実際のappとdoctorをmain経由で呼び、正常時0・欠損検出時1を確認する回帰テストを追加する。 3. 専用テストと全Python回帰、実sprout.exeでの手動再現、差分検査を行う。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
mainがTyper appから返された整数終了コードを伝播するよう修正し、実appとdoctorをmain経由で検証する回帰テストを追加した。検証: 対象4件成功、全回帰140 passed・2 skipped、実sprout.exeで正常時0・欠損時1、git diff --check成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Typer appの整数戻り値をmainから伝播し、doctorが正常時0・整合性問題検出時1を実コンソールで返すよう修正した。実app経由の回帰テストを追加し、全140件のPythonテストと手動終了コード確認で検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
