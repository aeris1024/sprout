---
id: TASK-46
title: doctor・stats・gcに構造化JSON出力を追加する
status: To Do
assignee: []
created_date: '2026-08-09 08:34'
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
- [ ] #1 doctor --jsonが正常状態、検査オブジェクト数、問題の種類と詳細を有効なJSONで返し、問題検出時の終了コード1を維持する
- [ ] #2 stats --jsonがコミット数、ブランチ数、追跡パス数、オブジェクト数と容量、論理容量、ユニーク容量、重複排除量を有効なJSONで返す
- [ ] #3 gc --jsonとgc --dry-run --jsonが対象オブジェクト・一時ファイル、件数、解放容量、dry-runか実処理かを有効なJSONで返す
- [ ] #4 --jsonを指定しない既存の人向け出力と各コマンドの変更・非変更動作が維持される
- [ ] #5 リポジトリ検出や処理エラーが--json指定時に構造化エラーとして返る
- [ ] #6 正常系・異常系・dry-run・実処理のCLIテストとREADMEの使用例が追加される
<!-- AC:END -->
