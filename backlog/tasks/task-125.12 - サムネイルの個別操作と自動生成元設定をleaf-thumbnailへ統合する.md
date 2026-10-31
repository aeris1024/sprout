---
id: TASK-125.12
title: サムネイルの個別操作と自動生成元設定をleaf thumbnailへ統合する
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
  - gui/src/App.tsx
  - gui/src-tauri/src/lib.rs
  - tests/test_cli.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 136000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在のthumbnailとcoverを別グループへ移すだけでなく、正規のサムネイル操作をleaf thumbnail配下へ集約する。個別の葉の確認・登録・変更・削除・取り出しに加え、自動生成元となる追跡画像の確認・指定・解除・既存葉への適用も同じ体系から操作する。file coverを正規の別入口として追加しない。
個別サムネイルは葉ごとのデータ、生成元の指定はプロジェクト単位の設定である。この対象範囲の差は明示し、生成元を扱う下位構文は着手時に確認する。commit/leaf createでの明示画像指定と自動生成の既存優先順位、既存葉へ適用するapplyを保持する。プレビューの代表指定と同一化するタスクではなく、previewの採否・整理方針は未決定。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 leaf thumbnailで葉ごとのshow/set/delete/exportと、自動生成元のshow/set/clear/apply相当を利用でき、独立したfile cover正規入口を不要にする
- [ ] #2 個別画像に必要なLEAF指定と、プロジェクト単位の生成元設定の対象範囲をヘルプ・引数で判別できる
- [ ] #3 leaf create時の明示画像と生成元の優先順位、生成できない場合の既存処理、画像の制約と原本を変更しない動作を維持する
- [ ] #4 既存葉への適用は登録済みサムネイルを保持し、dry-runで変更せず対象を確認できる。取り出しの既存上書き確認とJSON契約も維持する
- [ ] #5 生成元の素材ID・追跡解除・改名移動の扱いを維持し、GUIとRust側の取得を統合後の正規入口へ移行できる
- [ ] #6 previewの代表指定・素材関連付けの変更や削除を先取りせず、新構文・失敗時の無変更・serveを検証してV1形式を変更しない
<!-- AC:END -->
