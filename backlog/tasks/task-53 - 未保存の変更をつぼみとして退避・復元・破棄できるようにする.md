---
id: TASK-53
title: 未保存の変更をつぼみとして退避・復元・破棄できるようにする
status: To Do
assignee: []
created_date: '2026-10-27 15:03'
labels:
  - cli
  - gui-redesign
dependencies:
  - TASK-52
references:
  - src/sprout/repository.py
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: medium
type: feature
ordinal: 53000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

GUI刷新（doc-1、TASK-51）では、未保存の変更があるまま別のスナップショットへ移るとき、確認なしで変更を「つぼみ」として退避し、あとで戻れるようにする。

## ゴール

追跡ファイルの未保存の状態を、退避元の現在位置に紐づくつぼみとして保存し、一覧・復元・破棄できるようにする。つぼみの実体は既存のobjectsストアへ保存して重複排除を共有する。1つのスナップショットに複数のつぼみを付けられる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 追跡ファイルの未保存の状態を、退避元の現在位置・ブランチ・作成日時・変更ファイル情報とともにつぼみとして保存できる
- [ ] #2 つぼみの一覧を人向け出力とJSONで取得でき、treeのJSONで各スナップショットに付いたつぼみを確認できる
- [ ] #3 つぼみを復元すると作業ツリーが退避時の状態になり、現在位置が退避元になり、復元完了後にだけつぼみが削除される
- [ ] #4 復元時に別の未保存の変更がある場合は、それを先に新しいつぼみとして退避してから復元する
- [ ] #5 つぼみを破棄でき、破棄は明示的な指定がない限り行われない
- [ ] #6 未追跡ファイルは退避・復元で削除も上書きもされず、衝突やリンクがある場合は復元を中止する既存の保護が適用される
- [ ] #7 つぼみの実体がobjectsストアで重複排除され、gcが参照中のオブジェクトを削除せず、doctorとstatsがつぼみを検査・集計する
- [ ] #8 READMEとJSON契約が更新され、退避、一覧、復元、破棄、中断時の復旧、gc・doctor・statsとの整合がテストされる
<!-- AC:END -->
