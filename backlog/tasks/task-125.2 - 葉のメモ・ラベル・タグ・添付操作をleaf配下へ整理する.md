---
id: TASK-125.2
title: 葉のメモ・ラベル・タグ・添付操作をleaf配下へ整理する
status: To Do
assignee: []
created_date: '2026-10-31 07:23'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - src/sprout/preview_image.py
  - src/sprout/trash.py
  - tests/test_cli.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 126000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
leafに属する補足情報の入口を統一する。機能の削減は行わず、現行操作を次の構文へ整理する。
note -> leaf note show LEAF / set LEAF TEXT / delete LEAF
label -> leaf label list LEAF / add LEAF LABEL / delete LEAF LABEL
tag -> leaf tag list / create NAME [LEAF] / comment NAME TEXT / delete NAME
thumbnail -> leaf thumbnail show LEAF / set LEAF IMAGE / delete LEAF / export LEAF --output FILE
preview -> leaf preview list|add|replace|delete|export|order|edit|image。現在のpreview metadataはleaf preview editへ対応。
プレビューの表示名・説明・代表指定・素材関連付け・順序・不変添付IDを保持する。代表プレビューとサムネイル、file coverを同じ機能へ変更しない。既存GUI機能の追加やプレビュー機能削減は含めない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 メモ・ラベル・タグを正規のshow/set/list/add/create/comment/delete構文で管理でき、タグ作成の対象省略時は現在のブランチ先端を使う既存動作と作成コメント指定を保持する
- [ ] #2 サムネイルの確認・登録・変更・削除・取り出しと既存画像制約、上書き確認・JSONを利用できる
- [ ] #3 previewの8操作を新構文で利用でき、editで表示名・説明・代表指定・複数素材の関連を設定・解除できる
- [ ] #4 添付置き換え時のID・メタ情報保持、表示順、100 MiB超の確認、失敗時の無変更、ゴミ箱復旧と競合拒否を保持する
- [ ] #5 GUI向けimageの表示用データとJSON契約を維持し、関連する正規構文と拒否条件を自動テストで検証する
<!-- AC:END -->
