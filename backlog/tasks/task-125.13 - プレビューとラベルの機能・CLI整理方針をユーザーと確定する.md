---
id: TASK-125.13
title: 残るプレビュー仕様と具体的CLI配置をユーザーと確定する
status: To Do
assignee: []
created_date: '2026-10-31 07:33'
updated_date: '2026-10-31 08:56'
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
残るプレビュー仕様と具体的CLI配置をユーザーと確認する。次の方針は確定済み:
- 代表プレビューを廃止し、重要な添付は表示順で上へ移す（TASK-125.14）。
- プレビューの置き換えは維持する。
- サムネイルとプレビューを別機能として維持し、「代表ファイル」を「サムネイル自動生成元」へ改称して自動生成機能を維持する（TASK-125.12）。
- ラベルは複数の葉の分類として残す。全ブランチの現存する葉からプロジェクト全体のラベル一覧を提供し、GUIで既存ラベルを候補として選び、新規ラベルも入力できるようにする（TASK-125.15・TASK-125.16）。

未決定は、プレビューの素材関連付け、表示名・説明を含むその他の機能と具体的CLI配置。ラベルの維持・全体一覧・GUI候補表示を採否の判断待ちへ戻さない。ラベルの具体的な下位構文はTASK-125.15で正規CLI体系へ整合させ、ラベル廃止やGitタグへの置き換えは行わない。
未決定部分はユーザー判断前に機能・データ・利用経路を変更しない。今回の依頼はBacklog反映のみ。必要な決定後の実装・移行タスクと依存関係を追補する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 確定した代表指定の廃止・順序と置き換えの維持・サムネイル自動生成元への改称を記録し、TASK-125.14とTASK-125.12へ追跡できる
- [ ] #2 残るプレビューの素材関連付け・表示名/説明等とCLI配置の採否・整理方針をユーザーと確認して記録する
- [ ] #3 ラベル維持・プロジェクト全体一覧・GUI入力候補の確定方針をTASK-125.15・TASK-125.16へ追跡でき、採否を再び保留にしない
- [ ] #4 未決定のプレビュー仕様・具体的CLI配置はユーザーと確認し、確定済みのメディア方針やラベル維持とは区別する
- [ ] #5 残る決定後に必要な実装・移行・検証・依存関係をタスクへ反映し、未実装の作業を完了扱いにしない
<!-- AC:END -->
