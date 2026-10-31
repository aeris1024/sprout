---
id: TASK-125.1
title: 正規CLIグループとleafの基本操作を導入する
status: To Do
assignee: []
created_date: '2026-10-31 07:22'
updated_date: '2026-10-31 07:36'
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
親タスクの正規10入口の基盤とleafの基本操作を整える。対応はcommit -> leaf create -m TEXT、tree -> leaf tree、show -> leaf show LEAF、delete-commit -> leaf delete LEAF、prune -> leaf prune（タグ間と--all）、archive -> leaf archive --output DIR。V1保存形式とこれらの既存機能を維持する。
log/素材履歴はTASK-125.10、message/noteはTASK-125.11、go/switch/全体restoreはTASK-125.9、thumbnail/coverはTASK-125.12の操作統合を担当する。このタスクでleaf restore、file history、leaf note、file cover、branch switchを旧案どおり追加しない。
init/status/go/serveをトップレベルとし、bud/branch/file/trash/maintenanceへ領域を分ける。段階的な作業中の既存GUI動作を保持し、preview/LabelはTASK-125.13の判断前に仕様を確定しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 leaf create/tree/show/delete/prune/archiveの基本操作と正規グループを提供し、各操作の対応する既存オプション・JSON・確認要件を維持する
- [ ] #2 履歴検索・説明編集・移動・サムネイルはTASK-125.10・TASK-125.11・TASK-125.9・TASK-125.12で統合する範囲と重複せず、統合前の別入口を新たに確定しない
- [ ] #3 leaf deleteのゴミ箱復旧、参照の移動、タグによる保護と、leaf pruneの保護対象・取り消し不可・作業ファイルを変更しない挙動が維持される
- [ ] #4 現在のV1リポジトリをそのまま利用でき、既存JSONキー・構造、終了コード、エラーcode、標準出力の契約を不要に変更しない
- [ ] #5 基本操作・危険操作のdry-runと拒否時の無変更を新構文で検証し、段階的な移行中も既存のGUI呼び出しが利用できる
<!-- AC:END -->
