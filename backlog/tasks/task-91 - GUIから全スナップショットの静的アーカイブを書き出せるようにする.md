---
id: TASK-91
title: GUIから全スナップショットの静的アーカイブを書き出せるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:35'
labels:
  - gui
dependencies: []
references:
  - src/sprout/cli.py
  - src/sprout/archive.py
  - gui/src/App.tsx
  - gui/README.md
priority: low
type: feature
ordinal: 90000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-36で追加された`sprout archive`は、全スナップショットをSproutなしで閲覧できる静的なHTML・JSON・ファイルに展開する機能だが、GUIから実行できない。GUIだけを使う利用者も長期保存用のアーカイブを作成できるようにする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 GUIから出力先を選び、実行前にコミット数・ファイル数・推定容量・空き容量を確認できる。キャンセルすると何も書き出さない
- [ ] #2 空き容量が足りない場合は実行できず、理由が表示される。未完了のアーカイブを置き換える場合は実行前に分かる
- [ ] #3 完了時に出力先を表示し、失敗時は理由を通知する。作業ファイルと履歴は変更しない
- [ ] #4 アーカイブにゴミ箱の復旧データが含まれないことを実行前に確認できる
- [ ] #5 自動テストで確認、容量不足、キャンセル、失敗時の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->
