---
id: TASK-125.11
title: メッセージとメモの編集をleaf editへ統合する
status: To Do
assignee: []
created_date: '2026-10-31 07:33'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - src/sprout/trash.py
  - gui/src/App.tsx
  - tests/test_cli.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 135000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在のmessageとnoteを別々の入口へ移すだけでなく、保存済み葉の説明を変更する正規入口をleaf edit LEAFへ統合する。メッセージは--message TEXT、メモの設定・変更・削除も同じeditから明示的に操作する。メモの確認はleaf showへ集約し、leaf note show/set/deleteを独立した正規入口として増設しない。
Label機能の採否・編集方法は未決定。従来提案したmessage/note/labelの統合のうち、このタスクではmessage/noteまでを確定し、labelの廃止やeditへの取り込みは判断待ちにする。メモ削除の具体的フラグ名等は着手時に整える。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 leaf edit LEAF --message TEXTでメッセージを、同じleaf editでメモの設定・変更・明示的な削除を操作でき、leaf showで現在のメモを確認できる
- [ ] #2 別のleaf note正規入口を残さず、未指定のフィールドを変更しない。メッセージとメモを同時指定する場合は全体が成功するか全体を拒否する
- [ ] #3 既存のメッセージ・メモの長さや正規化、空メッセージ拒否、メモ削除のゴミ箱保存と復旧の挙動を保持する
- [ ] #4 保存ファイル・葉ID・親子関係を変更せず、入力検証・保存が失敗した場合に片方だけを書き換えない
- [ ] #5 Labelの採否・統合・削除はこのタスクでは確定せず、ユーザー確認前にLabelのCLI・GUI・保存データを変更しない
- [ ] #6 新構文の成功・不正入力・同時更新・明示削除・JSON・serveを検証し、V1形式を変更しない
<!-- AC:END -->
