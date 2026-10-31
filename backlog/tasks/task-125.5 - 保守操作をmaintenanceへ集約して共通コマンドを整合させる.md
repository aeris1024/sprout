---
id: TASK-125.5
title: 保守操作をmaintenanceへ集約して共通コマンドを整合させる
status: To Do
assignee: []
created_date: '2026-10-31 07:24'
updated_date: '2026-10-31 07:36'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
references:
  - src/sprout/cli.py
  - src/sprout/serve.py
  - tests/test_cli.py
  - tests/test_serve.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 129000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
stats -> maintenance stats、doctor -> maintenance doctor、gc -> maintenance gcへ整理する。
init [PATH]、status [PATH...]、go TARGET、serveはトップレベルに維持する。trashはlist/show/restore/purgeの正規操作を持つグループとして扱い、既存の意味・オプションを維持する。
初期化、状態確認、移動、ゴミ箱、保守、常駐モードは役割を混ぜない。serveは正規の階層化されたargvを受け付け、都度起動と同じ結果を返す。
追補: go/switch/全体restoreの動作統合はTASK-125.9が担当する。このタスクはgoのトップレベル配置と連携経路を扱い、旧goのブランチ選択等を統合後も不変とする条件を追加しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 maintenance stats/doctor/gcが現在の件数・容量、整合性検査、未参照オブジェクト回収を提供し、reportとdry-runの既存動作を保持する
- [ ] #2 gcは通常履歴・つぼみ・ゴミ箱に保護された実体を回収せず、検査や容量表示は作業ファイルを変更しない
- [ ] #3 trash list/show/restore/purgeで競合検査、dry-run、完全削除の確認、完全IDの指定とJSON契約を維持する
- [ ] #4 init/statusの既存機能を保持し、goの正規入口・連携経路をTASK-125.9で確認した移動方針にそろえる
- [ ] #5 serveのプロトコルを変更せず階層化された正規コマンドを実行でき、成功・失敗・JSON・終了コードが都度起動と一致する
<!-- AC:END -->
