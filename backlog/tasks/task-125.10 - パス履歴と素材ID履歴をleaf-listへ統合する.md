---
id: TASK-125.10
title: パス履歴と素材ID履歴をleaf listへ統合する
status: To Do
assignee: []
created_date: '2026-10-31 07:33'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
  - TASK-125.3
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - tests/test_cli.py
  - tests/test_serve.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 134000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在のlogとfile-historyを別グループへ配置し直すだけでなく、履歴検索の正規入口をleaf listへ統合する。leaf list [PATH]が現在のlog、leaf list --file-id FILE_IDが現在のfile-historyに対応する。file historyを正規の別入口として追加しない。手打ちaliasのlogも同じ履歴検索を呼び出す。
パス指定は現在のブランチのそのパスの内容変更履歴、素材ID指定は全ブランチにある同じ素材の各保存記録であり、内容が変わらない記録や改名を含む。この範囲と抽出条件の差を隠さず明示する。leaf treeは全体構造の表示として維持する。ラベル機能の採否・変更は未決定で、この統合で廃止を決めない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 leaf listの引数なし・PATH指定と--file-id FILE_IDで現在のlog/file-historyの用途を提供し、独立したfile history正規コマンドを不要にする
- [ ] #2 PATH指定は現在ブランチの内容変更履歴を保ち、素材ID指定は全ブランチの各保存記録・改名・パス・更新日時を欠落なく返す
- [ ] #3 履歴範囲と記録の抽出条件をヘルプと出力で判別でき、PATHと素材ID等の無効な指定組み合わせは無変更で拒否する
- [ ] #4 現在のlogの件数・oneline・JSON等を維持し、素材IDモードでの各オプションの対応範囲を明示して検証する。ラベル絞り込みの扱いは未決定のLabel方針を先取りしない
- [ ] #5 旧JSON利用箇所への影響を整理し、モードごとのデータ項目を維持するか変更が必要な契約を明示する。alias logとserveでも同じ検索結果を得られる
- [ ] #6 素材IDの不正形式・未出現パス・空の履歴・複数ブランチ・改名・内容不変の記録を検証し、V1形式を変更しない
<!-- AC:END -->
