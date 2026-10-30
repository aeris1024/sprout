---
id: TASK-88
title: GUIで葉のサムネイルを削除できるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:34'
labels:
  - gui
dependencies: []
references:
  - src/sprout/cli.py
  - gui/src/App.tsx
  - gui/src/lib/thumbnails.ts
  - gui/README.md
priority: medium
type: feature
ordinal: 87000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUIではサムネイルの登録と置き換えはできるが、削除はできない。`sprout thumbnail <commit> --delete`はCLIにのみ存在するため、誤って登録したサムネイルを外すにはCLIが必要になる。葉の詳細から削除できるようにする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 サムネイルがある葉の詳細から削除でき、サムネイルがない葉には削除操作が表示されない
- [ ] #2 削除前に確認が表示され、キャンセルすると何も変更しない
- [ ] #3 削除後はマップと葉の詳細に古いサムネイルが残らない
- [ ] #4 失敗時は理由を通知し、サムネイルの表示を変更しない
- [ ] #5 自動テストで削除、キャンセル、失敗時の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->
