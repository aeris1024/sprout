---
id: TASK-91
title: GUIから全スナップショットの静的アーカイブを書き出せるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:35'
updated_date: '2026-10-31 09:29'
labels:
  - gui
dependencies:
  - TASK-125.1
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
全履歴をSproutなしで閲覧できる静的HTML・JSON・通常ファイルへ展開する機能をGUIから実行できるようにする。正規CLIはTASK-125.1のleaf archive --output DIRとそのdry-runを使う。旧トップレベルarchiveを恒久的なGUI契約にしない。
実行前に件数・容量・未完了出力の扱いと、ゴミ箱の復旧データを含まないことを確認できるようにする。これは静的な閲覧/取り出し用アーカイブであり、ゴミ箱やDB復旧を含むプロジェクト全体のバックアップとは区別する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 GUIから出力先を選び、実行前にコミット数・ファイル数・推定容量・空き容量を確認できる。キャンセルすると何も書き出さない
- [ ] #2 空き容量が足りない場合は実行できず、理由が表示される。未完了のアーカイブを置き換える場合は実行前に分かる
- [ ] #3 完了時に出力先を表示し、失敗時は理由を通知する。作業ファイルと履歴は変更しない
- [ ] #4 アーカイブにゴミ箱の復旧データが含まれないことを実行前に確認できる
- [ ] #5 自動テストで確認、容量不足、キャンセル、失敗時の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->
