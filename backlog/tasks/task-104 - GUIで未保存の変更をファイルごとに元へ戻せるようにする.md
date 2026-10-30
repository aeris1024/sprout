---
id: TASK-104
title: GUIで未保存の変更をファイルごとに元へ戻せるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/SavePanel.tsx
  - gui/src/App.tsx
  - src/sprout/cli.py
  - gui/README.md
priority: medium
type: feature
ordinal: 103000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
未保存の変更の一覧は表示だけで、変更を破棄する操作やファイルごとの操作がない。破棄するには、葉の詳細の保存済みファイルから対象を選んで戻す必要があり、新しく追加したファイルの扱いも分かりにくい。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 未保存の変更の一覧から、選んだファイルの変更を現在位置の内容へ戻せる
- [ ] #2 戻す前に対象と、変更内容が失われることを確認でき、キャンセルすると何も変更しない
- [ ] #3 追加のファイルと削除のファイルで、戻した結果が実行前に分かる。未追跡ファイルを無断で削除しない
- [ ] #4 実行後は未保存の変更、上部バー、マップが更新され、失敗時は理由を通知する
- [ ] #5 自動テストで変更・追加・削除それぞれとキャンセルを検証し、gui/README.mdを更新する
<!-- AC:END -->
