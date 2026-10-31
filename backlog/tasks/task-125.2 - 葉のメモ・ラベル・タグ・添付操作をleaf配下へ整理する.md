---
id: TASK-125.2
title: 葉のタグ操作をleaf配下へ整理する
status: To Do
assignee: []
created_date: '2026-10-31 07:23'
updated_date: '2026-10-31 07:52'
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
タグ操作をleaf tag list / create NAME [LEAF] / comment NAME TEXT / delete NAMEへ整理する。タグの現在の参照・コメント・保護・削除復旧の意味を維持する。
旧タスクのメモはTASK-125.11のleaf edit統合へ、サムネイルはTASK-125.12の個別操作と生成元の統合へ切り出した。代表プレビュー廃止と置き換え維持はTASK-125.14で扱う。素材関連付け・Label等の未決定部分はTASK-125.13の判断待ちであり、このタグ操作タスクでは変更しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 leaf tag list/create/comment/deleteで現在のタグ機能を利用でき、対象省略時の現在ブランチ先端、作成コメント・コメントの解除を保持する
- [ ] #2 タグ付き葉の保護、タグだけを削除する動作、ゴミ箱からの復旧と名前衝突時の拒否を保持する
- [ ] #3 タグの成功・不正入力・衝突・JSON・serveを正規構文で検証し、list/create等の文字列もタグ名として扱える
- [ ] #4 メモ・サムネイル・代表プレビュー廃止は各対応タスクへ委ね、素材関連付け・Label等の未決定部分はユーザー確認前に変更しない
<!-- AC:END -->
