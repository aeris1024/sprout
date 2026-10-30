---
id: TASK-104
title: GUIで未保存の変更をファイルごとに元へ戻せるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 17:54'
updated_date: '2026-10-30 21:45'
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
- [x] #1 未保存の変更の一覧から、選んだファイルの変更を現在位置の内容へ戻せる
- [x] #2 戻す前に対象と、変更内容が失われることを確認でき、キャンセルすると何も変更しない
- [x] #3 追加のファイルと削除のファイルで、戻した結果が実行前に分かる。未追跡ファイルを無断で削除しない
- [x] #4 実行後は未保存の変更、上部バー、マップが更新され、失敗時は理由を通知する
- [x] #5 自動テストで変更・追加・削除それぞれとキャンセルを検証し、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 変更一覧の行に操作を追加: 変更/削除は restore <現在位置> <path> --discard、追加は untrack 2. 確認ダイアログで対象と影響を表示、キャンセルで無変更 3. 改名は対象外 4. テストとgui/README.md更新
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
revertUnsavedを実装。追加は追跡解除のみでファイルを削除しない。改名は2パスにまたがるため操作を出さない。実CLIで restore --discard(変更/削除)と untrack がファイルを残すことを確認。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
未保存の変更一覧から変更・削除を現在位置の内容へ戻す、追加を追跡から外す操作を追加。確認ダイアログとキャンセル、失敗通知、再取得を実装し、改名は対象外とした。変更・削除・追加・キャンセル・失敗・改名のテストを追加し、vitest全159件とtscが成功。
<!-- SECTION:FINAL_SUMMARY:END -->
