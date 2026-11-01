---
id: TASK-117
title: GUIの比較結果で長いパスの全体を確認できるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-30 21:29'
updated_date: '2026-11-01 05:15'
labels:
  - gui
dependencies: []
references:
  - gui/src/components/ComparePanel.tsx
  - gui/src/App.css
priority: low
type: enhancement
ordinal: 116000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
スナップショットの比較結果では、長いパスが省略表示されるが、ファイルパネルと違って全体を確認する手段がない。TASK-95でファイルパネルの行を修正した際に見つかった。改名の行は元のパスと新しいパスを並べて表示するため、さらに省略されやすい。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 比較結果の行で省略されたパスの全体を、ポインタを重ねるかキーボードで確認できる
- [x] #2 改名の行では元のパスと新しいパスの両方を確認できる
- [x] #3 長いパスでも比較パネルに横スクロールが出ず、サイズの表示が隠れない
- [x] #4 自動テストで全体の確認方法と改名の行を検証する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 比較結果のパスをキーボードで開ける詳細へし、ポインタのtitleにも全文を用意する。 2. 改名前後の両パスを表示し、折り返しでも容量が隠れない配置を検証する。 3. 自動テストと狭いパネルのブラウザー検証を行う。
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
比較結果のパスにtitleと開閉式の全文表示を追加し、改名前後を個別表示。既存275テスト成功、新規テストはjsdomのsummaryキー既定動作未対応に合わせて開閉検証へ修正し比較6テスト成功。ビルド成功。PlaywrightでEnter展開、280pxパネルの横はみ出し防止と容量表示を検証。
<!-- SECTION:FINAL_SUMMARY:END -->
