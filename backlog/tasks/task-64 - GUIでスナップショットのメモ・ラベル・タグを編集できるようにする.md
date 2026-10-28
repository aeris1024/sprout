---
id: TASK-64
title: GUIでスナップショットのメモ・ラベル・タグを編集できるようにする
status: To Do
assignee: []
created_date: '2026-10-28 16:58'
labels: []
dependencies:
  - TASK-63
references:
  - gui/src/components/CommitPanel.tsx
  - gui/src/App.tsx
  - src/sprout/cli.py
  - src/sprout/repository.py
priority: medium
type: feature
ordinal: 64000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
メモ・ラベル・タグはCLIで操作できるが、GUIでは表示も編集もできない。またtagコマンドはJSON出力に対応しておらず、常に--jsonを付けて呼び出すGUIからは使えない。タグのコメントは作成後に変更できない。

スナップショットの詳細から、メモ・ラベル・タグを確認・編集できるようにする。

対象外: タグの名前変更、ラベルによる絞り込み表示。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tagコマンドが作成・削除・一覧・コメント変更でJSONを出力し、既存のテキスト出力と名前による操作を維持する
- [ ] #2 CLIで既存タグのコメントを変更でき、存在しないタグは構造化エラーで拒否される
- [ ] #3 スナップショットの詳細でメモを表示・編集・削除でき、上限を超えるメモはエラーとして通知され入力内容が失われない
- [ ] #4 スナップショットの詳細でラベルを一覧・追加・削除でき、空・長すぎる・上限数を超えるラベルはエラーとして通知される
- [ ] #5 スナップショットの詳細でタグをコメント付きで一覧・作成・コメント変更・削除でき、削除前に確認が表示される
- [ ] #6 編集後にマップと詳細の表示が更新され、コミットID・親子関係・ファイル・添付・ブランチは変化しない
- [ ] #7 CLIとGUIの自動テストで各操作と入力エラーを検証し、READMEとgui/READMEを更新する
<!-- AC:END -->
