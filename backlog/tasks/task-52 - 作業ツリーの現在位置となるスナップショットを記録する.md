---
id: TASK-52
title: 作業ツリーの現在位置となるスナップショットを記録する
status: To Do
assignee: []
created_date: '2026-10-27 15:03'
labels:
  - cli
  - gui-redesign
dependencies: []
references:
  - src/sprout/repository.py
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: medium
type: feature
ordinal: 52000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

GUI刷新（doc-1、TASK-51）では、作業ツリーがどのスナップショットに基づいているか（現在位置）を芽のマップに表示し、移動・退避・保存の起点として使う。現在のrestoreは作業ツリーを書き戻すだけで位置を記録せず、ブランチ先端以外を表示中かどうかはファイル内容の一致から推測している。

## ゴール

現在位置をリポジトリに記録し、restore・switch・commit・ブランチ作成時の切り替えで一貫して更新する。CLIとJSON出力から現在位置と、それがブランチ先端かどうかを取得できるようにする。保存形式は正式リリース前のVersion 1のまま拡張し、移行処理は設けない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 全体restore、switch、branch --switch、commitの成功後に現在位置が対象スナップショットへ更新される
- [ ] #2 部分restoreや失敗・中断した操作では現在位置が変わらないか、操作前の値へ復旧される
- [ ] #3 statusとtreeのJSON出力に現在位置のコミットIDと、それが現在ブランチの先端かどうかが含まれ、人向けstatusにも先端以外を表示中であることが示される
- [ ] #4 コミットがない新規リポジトリでは現在位置が空として扱われる
- [ ] #5 ブランチ先端以外を表示中に起点省略のブランチ作成を拒否する既存の保護が、記録した現在位置に基づいて動作する
- [ ] #6 pruneやブランチ削除で現在位置のコミットが失われない、または失われる操作が拒否される
- [ ] #7 READMEとJSON契約が更新され、各操作での現在位置の更新と非更新がテストされる
<!-- AC:END -->
