---
id: TASK-125.13
title: プレビューとラベルの機能・CLI整理方針をユーザーと確定する
status: To Do
assignee: []
created_date: '2026-10-31 07:33'
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
ユーザーはプレビュー周りとLabel周りの整理をまだ検討中。既存TASK-125では全機能維持と新しい正規構文を一律に確定していたが、この2領域の機能採否・統合・削除・CLI配置は未確定として切り離す。
プレビューは添付の基本管理、表示名・説明、代表指定、素材関連付け等を分けて扱う。Labelはタグ・メモとの役割や履歴絞り込みへの影響を含め検討する。仕様を確認するタスクであり、先行して機能や保存データを削除しない。ユーザーが決めるまでは現在の機能・CLI・GUIの利用経路を保持する。
決定後、必要な実装はユーザーの依頼・承認の範囲で既存タスクを更新または追加し、alias・GUI移行・ヘルプ・統合検証への依存関係を整える。今回の4系統の統合は、未決定のpreview/Labelの採否を勝手に決めずに仕様を整理できる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 プレビューの基本添付管理・表示名/説明・代表指定・素材関連付けについて、維持・統合・削減の判断と理由をユーザーと確認して記録する
- [ ] #2 Labelの役割、タグ・メモとの違い、履歴検索やGUIへの影響を整理し、残すか、leaf edit等へ統合するか、削減するかをユーザーと確認して記録する
- [ ] #3 未決定中はpreview/Labelの機能・保存データ・既存呼び出し経路を維持し、保留を実装済みや仕様確定として扱わない
- [ ] #4 決定後に必要な実装範囲と移行・検証・依存関係をタスクへ反映し、機能削減やV1保存データの変更が必要なら別途明示して承認を得る
<!-- AC:END -->
