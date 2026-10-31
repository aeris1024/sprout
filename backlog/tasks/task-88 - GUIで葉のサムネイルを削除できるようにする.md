---
id: TASK-88
title: GUIで葉のサムネイルを削除できるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:34'
updated_date: '2026-10-31 09:28'
labels:
  - gui
dependencies:
  - TASK-125.12
  - TASK-126
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
既存の葉サムネイル削除機能をGUIから使えるようにする。CLI再編後はTASK-125.12のleaf thumbnail deleteを正規の呼び出し先とする。
TASK-126の補助メニューと整合する入口から削除できるようにし、同じ操作のために詳細上部へ常時ボタンを増やさない。サムネイルがある場合だけ表示し、削除確認・キャンセル・失敗通知・表示更新を扱う。サムネイルの削除と葉そのものの削除を区別し、葉の削除に固有のタグ保護制限をサムネイル削除へ流用しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 サムネイルがある葉の詳細から削除でき、サムネイルがない葉には削除操作が表示されない
- [ ] #2 削除前に確認が表示され、キャンセルすると何も変更しない
- [ ] #3 削除後はマップと葉の詳細に古いサムネイルが残らない
- [ ] #4 失敗時は理由を通知し、サムネイルの表示を変更しない
- [ ] #5 自動テストで削除、キャンセル、失敗時の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->
