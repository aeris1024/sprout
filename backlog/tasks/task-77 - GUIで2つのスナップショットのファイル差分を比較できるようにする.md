---
id: TASK-77
title: GUIで2つのスナップショットのファイル差分を比較できるようにする
status: To Do
assignee: []
created_date: '2026-10-29T16:34:00Z'
labels: []
dependencies: []
references:
  - src/sprout/cli.py
  - gui/src/components/SproutMap.tsx
  - gui/src/components/CommitPanel.tsx
  - gui/src/App.tsx
priority: high
type: feature
ordinal: 76000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
制作中に過去の版へ戻ったり別の枝の成果を使ったりする際、現在のGUIでは葉のメッセージやサムネイルだけで判断する必要があり、どのファイルが変わったかを確認できない。CLIの sprout diff COMMIT_A COMMIT_B を利用し、葉のマップから選んだ2つのスナップショットを作業ファイルを変えずに比較できるようにする。対象はファイル単位の追加・変更・削除であり、テキスト本文の差分や画像・動画の内容比較は含めない。ファイルの取り出し・部分復元、preview添付の管理（TASK-72）は別タスクで扱う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 芽のマップから比較元と比較先の2つのスナップショットを指定し、ファイル差分を表示できる
- [ ] #2 比較元から比較先への方向と、双方のコミットID・メッセージを画面で確認できる
- [ ] #3 追加・変更・削除を区別し、対象ファイルのパスを一覧できる。結果はCLIの diff と一致する
- [ ] #4 差分がない場合はその旨を表示し、比較対象を変更して再比較できる
- [ ] #5 比較は作業ファイル・追跡状態・現在位置・ブランチ先端を変更しない。失敗時は構造化エラーを表示して再試行できる
- [ ] #6 比較対象の指定、追加・変更・削除、差分なし、失敗時の表示を検証する自動テストと、gui/README.md の操作説明が追加される
<!-- AC:END -->
