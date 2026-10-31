---
id: TASK-125.1
title: 正規CLIグループとleafの基本操作を導入する
status: To Do
assignee: []
created_date: '2026-10-31 07:22'
labels:
  - cli
  - usability
dependencies: []
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - src/sprout/archive.py
  - tests/test_cli.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 125000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
親タスクの正規10入口を利用できる体系とし、保存済み状態の基本操作をleaf配下へ整理する。既存の機能・オプションとV1保存形式を維持する。個別実装の手順は着手時に調査して決める。
対応: commit -> leaf create -m TEXT、log [PATH] -> leaf list [PATH]、tree -> leaf tree、show -> leaf show LEAF、message -> leaf edit LEAF --message TEXT、全体restore -> leaf restore LEAF、delete-commit -> leaf delete LEAF、prune -> leaf prune（タグ間と--all）、archive -> leaf archive --output DIR。
init/status/go/serveはトップレベル、bud/branch/file/trash/maintenanceを正規グループとして扱う。残りの下位操作は同じ親の各領域タスクで追加する。段階的な移行中に既存GUI・CLIの動作が失われないこと。恒久的なaliasは別タスクで合意済み一覧にそろえる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 leaf create/list/tree/show/edit/restore/delete/prune/archiveの各操作が対応する既存コマンドと同じ結果を返し、パス・件数・ラベル・日時・サムネイル・dry-run・確認等の既存オプションを利用できる
- [ ] #2 leaf restoreはブランチを切り替えず全体を復元する既存動作を保持し、goの自動退避や切り替え規則と混同しない
- [ ] #3 leaf deleteのゴミ箱復旧、参照の移動、タグによる保護と、leaf pruneの保護対象・取り消し不可・作業ファイルを変更しない挙動が維持される
- [ ] #4 現在のV1リポジトリをそのまま利用でき、既存JSONキー・構造、終了コード、エラーcode、標準出力の契約を不要に変更しない
- [ ] #5 基本操作・危険操作のdry-runと拒否時の無変更を新構文で検証し、段階的な移行中も既存のGUI呼び出しが利用できる
<!-- AC:END -->
