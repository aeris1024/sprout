---
id: TASK-95
title: GUIのファイルパネルで長いパスでも操作ボタンを押せるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 17:53'
updated_date: '2026-10-30 18:28'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/FilePanel.tsx
  - gui/src/App.css
priority: high
type: bug
ordinal: 94000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ファイルパネルでは、パスが長いと行の「追跡解除」「追跡する」ボタンがパネルの外へ押し出され、横スクロールしないと押せない。幅1280pxの画面で長い日本語ファイル名を持つ240ファイルのプロジェクトを開くと、ボタンの左端がx=1283になることを確認した。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 パスの長さに関係なく、追跡解除・追跡するボタンが横スクロールなしで表示され、押せる
- [x] #2 省略されたパスの全体を確認できる
- [x] #3 パネル全体に不要な横スクロールが出ない
- [x] #4 自動テストまたはレイアウト検証で、長いパスの行の表示を確認する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Give .panel-section and .file-list a minmax(0,1fr) column so a nowrap path cannot widen the panel; 2. Keep the row button unshrunk and on one line; 3. Measure the real GUI with long paths for the file panel and the compare panel at 1280px; 4. Add a component test for the full path title and the row actions.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Cause: .panel-section and .file-list grids used an implicit auto column, so a nowrap path widened the column past the panel. Both now use minmax(0, 1fr) and the row button keeps its size. Measured in the real GUI (headless Edge, CLI bridged) with 240 long-named files: at 1280px panel scrollWidth 304 = clientWidth 304, button right edge max 1241 within content edge 1264, previously button left 1283; elementFromPoint hits the button; all 240 truncated paths have a title with the full path. At 700px scrollWidth = clientWidth (685). Compare panel (shared .file-row): scrollWidth = clientWidth (319), row right edge 1264. pnpm test 110 passed, pnpm build OK.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed file panel rows so the track and untrack buttons stay visible for any path length, with the path truncated and readable through its title, and no horizontal panel scroll. Verified by layout measurement in the real GUI at 1280px and 700px, the compare panel check, a new FilePanel component test, pnpm test and pnpm build.
<!-- SECTION:FINAL_SUMMARY:END -->
