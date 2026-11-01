---
id: TASK-100
title: GUIの比較で比較元と比較先をマップ上で分かるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-30 17:54'
updated_date: '2026-11-01 05:13'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/ComparePanel.tsx
  - gui/src/components/SproutMap.tsx
  - gui/src/App.tsx
  - gui/README.md
priority: medium
type: enhancement
ordinal: 99000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
スナップショットの比較中は、比較元と比較先がマップ上で強調されず、右パネルのIDとメッセージでしか確認できない。マップのクリックで選べるのは比較先だけで、比較元の変更は選択欄に限られる。結果のサイズもバイト数のままで読みにくい。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 比較中は比較元と比較先の葉がマップ上で区別して表示される
- [x] #2 マップから比較元と比較先の両方を選び直せる。比較元と比較先を入れ替えられる
- [x] #3 比較結果のサイズが読みやすい単位で表示される
- [x] #4 比較を閉じると強調が消え、比較は作業ファイルと現在位置を変更しない
- [x] #5 自動テストで強調、選び直し、入れ替えを検証し、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 比較元/先をマップ上の札と枠で区別し、選び直す側を比較パネルで指定できるようにする。 2. 元/先の入れ替えと読みやすい容量単位を追加し、比較を閉じた時に強調を消す。 3. マップ選択・入れ替え・強調解除・作業フォルダ不変をテストとブラウザーで検証しREADMEを更新する。
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
比較元/先の札と異なる枠、マップで選び直す側のラジオ選択、入れ替えと容量単位の整形を追加。比較解除時の強調解除と作業フォルダを変更しない呼び出しを統合テストで確認。GUI275テストとビルド成功。
<!-- SECTION:FINAL_SUMMARY:END -->
