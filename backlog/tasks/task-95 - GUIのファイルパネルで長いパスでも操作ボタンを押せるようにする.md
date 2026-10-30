---
id: TASK-95
title: GUIのファイルパネルで長いパスでも操作ボタンを押せるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:53'
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
- [ ] #1 パスの長さに関係なく、追跡解除・追跡するボタンが横スクロールなしで表示され、押せる
- [ ] #2 省略されたパスの全体を確認できる
- [ ] #3 パネル全体に不要な横スクロールが出ない
- [ ] #4 自動テストまたはレイアウト検証で、長いパスの行の表示を確認する
<!-- AC:END -->
