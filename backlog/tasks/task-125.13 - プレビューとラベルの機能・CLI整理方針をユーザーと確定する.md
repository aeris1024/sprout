---
id: TASK-125.13
title: プレビューとラベルの機能・CLI整理方針をユーザーと確定する
status: To Do
assignee: []
created_date: '2026-10-31 07:33'
updated_date: '2026-10-31 07:50'
labels:
  - cli
  - needs-decision
dependencies: []
references:
  - gui/src/components/PreviewPanel.tsx
  - gui/src/components/CommitAnnotations.tsx
  - src/sprout/cli.py
  - src/sprout/repository.py
  - README.md
parent_task_id: TASK-125
priority: low
type: spike
ordinal: 137000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
プレビューとLabelの整理について、残る未決定事項をユーザーと確認する。現時点で次の方針は確定済み:
- 代表プレビューは廃止し、重要な添付は表示順で上へ移す（TASK-125.14）。
- プレビューの置き換えは維持する。同じ一覧項目のID・順序・説明等を保ち、中身だけを修正する。
- サムネイルとプレビューを別機能として維持する。
- 「代表ファイル」は「サムネイル自動生成元」へ改称し、自動生成機能を維持する（TASK-125.12）。

残る検討は、プレビューの素材関連付け、表示名・説明を含むその他の機能とCLI配置、Labelの役割・タグやメモとの違い・履歴絞り込みへの影響。これらの採否・統合・削減を先取りしない。
確定した方針は実装タスクへ記録済みだが、今回の依頼はBacklog反映のみ。未決定部分は現行機能・保存データ・利用経路を保持する。残る決定後に必要な実装・移行タスクとalias・GUI・文書・検証の依存関係を追補する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 確定した代表指定の廃止・順序と置き換えの維持・サムネイル自動生成元への改称を記録し、TASK-125.14とTASK-125.12へ追跡できる
- [ ] #2 残るプレビューの素材関連付け・表示名/説明等とCLI配置の採否・整理方針をユーザーと確認して記録する
- [ ] #3 Labelの役割、タグ・メモとの違い、履歴検索やGUIへの影響を整理し、残すか、leaf edit等へ統合するか、削減するかをユーザーと確認して記録する
- [ ] #4 未決定部分の機能・データ・呼び出しは判断前に変更せず、確定済みの代表指定廃止と置き換え維持を一括した判断待ちへ戻さない
- [ ] #5 残る決定後に必要な実装・移行・検証・依存関係をタスクへ反映し、未実装の作業を完了扱いにしない
<!-- AC:END -->
