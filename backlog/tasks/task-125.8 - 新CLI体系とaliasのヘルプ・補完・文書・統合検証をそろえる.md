---
id: TASK-125.8
title: 新CLI体系とaliasのヘルプ・補完・文書・統合検証をそろえる
status: To Do
assignee: []
created_date: '2026-10-31 07:24'
updated_date: '2026-10-31 07:37'
labels:
  - cli
  - docs
  - usability
dependencies:
  - TASK-125.6
  - TASK-125.7
  - TASK-125.13
references:
  - README.md
  - gui/README.md
  - src/sprout/cli.py
  - tests/test_cli.py
  - tests/test_serve.py
  - scripts/create_sample_repo.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 132000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
親タスクの正規10入口と合意したaliasを、ヘルプ・シェル補完・README・利用例・テストで一貫して使える状態にする。
各CLI領域のタスクがその操作の回帰検証を持ち、このタスクでは全体の対応漏れ、利用導線、階層化されたコマンドとaliasの補完、外部連携経路の整合を確認する。既存33トップレベルとpreview下位操作から新構文への対応表を残す。
通常ヘルプは正規体系を中心とし、手打ちaliasの一覧と使い方に到達できる。Git名のaliasもSproutの挙動であること、trackにステージングがないこと、stash popがつぼみを消費することを明記する。
追補: go系・log系・message系・thumbnail系の配置変更と操作統合を区別し、最終の正規入口・alias・挙動差を説明する。重複するbranch switch/leaf restore/file history/leaf note/file coverは正規一覧へ戻さない。preview/LabelはTASK-125.13でユーザーと確認した扱いと必要な追補実装を確認してから最終一覧を確定する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 READMEのクイックスタート・全コマンド一覧・各機能例・JSON例とGUI READMEのCLI説明が新構文に整合し、旧33入口からの対応を確認できる
- [ ] #2 rootと各下位操作のhelpが整合し、基本10入口・用途・必須引数・alias対応を迷わず確認できる
- [ ] #3 PowerShell/bash/zshで階層化されたコマンドと対応aliasの補完、および葉・ブランチ・タグ参照の既存補完が機能することを検証する
- [ ] #4 基本の保存から履歴閲覧・分岐・退避・復元・取り出し、添付管理、ゴミ箱、prune、保守まで、正規CLIの対応漏れがないことを統合検証する
- [ ] #5 CLI・serve・alias・GUIの関連テストと必要なビルドが成功し、既存V1リポジトリとサンプルを正規構文で利用できる
- [ ] #6 4系統の統合結果を正規CLIとaliasで説明でき、TASK-125.13でpreview/Labelの扱いをユーザーと確認し、決定後に必要な実装・移行タスクの反映と完了を確認してから全体を完了する
<!-- AC:END -->
