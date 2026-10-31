---
id: TASK-125.14
title: 代表プレビュー指定を廃止し表示順と置き換え機能を維持する
status: To Do
assignee: []
created_date: '2026-10-31 07:49'
labels:
  - cli
  - gui
  - usability
dependencies: []
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - src/sprout/archive.py
  - src/sprout/trash.py
  - gui/src/components/PreviewPanel.tsx
  - gui/src/App.tsx
  - tests/test_preview_metadata.py
  - tests/test_previews.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 138000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ユーザーが確定したプレビュー整理方針を実装する。代表プレビューの独立した指定・解除・表示を廃止し、重要な添付は既存の表示順で先頭へ移動できるようにする。サムネイルとプレビューは別機能として維持する。
プレビューの置き換えは残す。同じ一覧項目のまま中身だけを差し替える操作として、添付ID・表示位置・作成日時・表示名・説明・素材関連付けを維持し、置き換え前の内容はゴミ箱に保持する。素材関連付け自体の採否はTASK-125.13で未決定のため、このタスクでは削除しない。
対象にはGUIの代表チェック・代表バッジ、CLIの代表指定オプション、JSON・アーカイブ・ゴミ箱復旧・テスト・文書の整合を含める。既存is_primaryの保存上の扱いも整理するが、添付原本・表示順や他のメタ情報を巻き添えに消さない。V1方針を維持し、バージョン番号の引き上げや保存形式の旧版互換処理をこのタスク登録で追加決定しない。今回の依頼はBacklog反映だけであり、実装は未着手。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 GUIとCLIで代表プレビューを指定・解除する操作と代表表示を廃止し、JSON・アーカイブ・ヘルプ・文書も代表という概念に依存しない
- [ ] #2 プレビューの順序を保存・復元でき、先頭へ移すことで重要な添付を上に置ける。順番の変更でサムネイルや添付内容を変更しない
- [ ] #3 追加・削除・取り出し・表示と置き換えを維持し、置き換えではID・位置・作成日時・表示名・説明・現在の素材関連付けを維持する
- [ ] #4 置き換え前の内容をゴミ箱から従来の競合条件で復旧でき、代表指定が復旧によって再び有効な機能として現れない
- [ ] #5 既存の代表指定を含むデータ・復旧記録の扱いを整理し、プレビュー原本・順序・他のメタ情報を失わず、V1方針と整合する
- [ ] #6 代表指定廃止と順序・置き換え・復旧・失敗時の無変更をCLI/GUI/serve/アーカイブの関連テストで検証する
- [ ] #7 素材関連付けとLabelの採否はこのタスクでは決めず、TASK-125.13の未決定事項として保持する
<!-- AC:END -->
