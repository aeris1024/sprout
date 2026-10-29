---
id: TASK-72
title: GUIでコミットのpreviewを追加・置き換え・削除・並べ替え・取り出しできるようにする
status: To Do
assignee: []
created_date: '2026-10-29T14:58:00Z'
updated_date: '2026-10-29T16:35:00Z'
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
- [ ] #1 葉の詳細でpreviewを保存された表示順に一覧し、元ファイル名・media_type・サイズを確認できる
- [ ] #2 ファイル選択で1件以上のpreviewを追加でき、形式を問わず登録できる
- [ ] #3 葉の詳細を表示中のCtrl+Vで、クリップボードの画像やファイルをpreviewとして追加できる（サムネイル貼り付けとの使い分けが明確）
- [ ] #4 添付IDで指定したpreviewを個別に置き換え・削除・任意の出力先へ取り出せる
- [ ] #5 previewの表示順を変更して保存でき、再読み込み後も順序が保たれる
- [ ] #6 100 MiBを超えるファイルは登録前にサイズと容量影響を表示し、確認後にだけ登録する
- [ ] #7 操作が失敗したときは構造化エラーを表示し、既存のpreviewと表示順を変更しない
- [ ] #8 自動テストとgui/README.mdが更新される
<!-- AC:END -->
