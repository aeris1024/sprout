---
id: TASK-72
title: GUIでコミットのpreviewを追加・置き換え・削除・並べ替え・取り出しできるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-29T14:58:00Z'
updated_date: '2026-10-29T17:05:00Z'
labels: []
dependencies:
  - TASK-38
  - TASK-71
references:
  - gui/src/components/CommitPanel.tsx
  - gui/src/App.tsx
  - gui/src/lib/clipboard.ts
priority: high
type: feature
ordinal: 72000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

TASK-38でCLI（sprout preview list/add/replace/delete/export/order）と保存層は複数previewに対応したが、GUIは葉の詳細で添付を一覧表示するだけで、previewを管理できない。サムネイルはTASK-71でクリップボード貼り付けに対応した。

## ゴール

GUIの葉の詳細から、previewの追加（ファイル選択・ドラッグ＆ドロップ・Ctrl+V貼り付け）、置き換え、削除、取り出し、並べ替えをCLI経由で行えるようにする。音声・動画・3Dなどの再生・表示はTASK-39・TASK-40・TASK-41で扱い、本タスクでは形式に関係なく汎用ファイルとして管理できることを重視する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 葉の詳細でpreviewを保存された表示順に一覧し、元ファイル名・media_type・サイズを確認できる
- [x] #2 ファイル選択で1件以上のpreviewを追加でき、形式を問わず登録できる
- [x] #3 葉の詳細を表示中のCtrl+Vで、クリップボードの画像やファイルをpreviewとして追加できる（サムネイル貼り付けとの使い分けが明確）
- [x] #4 添付IDで指定したpreviewを個別に置き換え・削除・任意の出力先へ取り出せる
- [x] #5 previewの表示順を変更して保存でき、再読み込み後も順序が保たれる
- [x] #6 100 MiBを超えるファイルは登録前にサイズと容量影響を表示し、確認後にだけ登録する
- [x] #7 操作が失敗したときは構造化エラーを表示し、既存のpreviewと表示順を変更しない
- [x] #8 自動テストとgui/README.mdが更新される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 葉の詳細にpreview管理パネルを追加しCLIのdry-run・追加・置換・削除・export・順序保存を接続する。2. preview貼り付け用のフォーカス領域と任意形式一時ファイル保存を追加し、サムネイル貼り付けと区別する。選択中の葉へドロップしたファイルをpreviewへ追加する。3. 大容量確認、失敗時保持、一時ファイル清掃を含むGUI・Rust・CLIテストとビルド、操作説明を検証する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
検証: GUI 94件、Rust 8件、CLI 382件成功（19件skip）、TypeScript + Vite build成功。DOMテストで大容量登録の承認/キャンセル、複数ファイルのドロップ、添付IDによる置換・削除・並べ替え、上書きなしexport、失敗時の表示順保持、任意形式と画像のpreview貼り付け、サムネイルとの分離、一時ファイルの失敗時清掃、Explorerのネイティブファイル参照の接続を確認。Rustテストで任意形式・空ファイルの保存/清掃と危険なファイル名の拒否を確認。Windows API連携はコンパイル/リンクとGUIモックで検証し、実機クリップボードの手動操作は未実施。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
葉の詳細にpreview管理パネルを追加し、任意形式の追加・置換・削除・取り出し・順序保存に対応した。選択中の葉へのファイルドロップと専用領域でのCtrl+Vを追加。100 MiB超はCLI dry-runのサイズ/容量表示と確認後に登録。一時ファイル処理とExplorerのCF_HDROP参照を追加し、既存のサムネイル貼り付けを維持。音声・動画・3Dの再生表示は既存の別タスクの範囲。操作説明とテストを更新。
<!-- SECTION:FINAL_SUMMARY:END -->
