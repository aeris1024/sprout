---
id: TASK-56
title: 未保存変更の判定でファイル全体のハッシュ計算を省略して高速化する
status: To Do
assignee: []
created_date: '2026-10-27 15:03'
labels:
  - cli
  - performance
dependencies: []
references:
  - src/sprout/repository.py
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: medium
type: enhancement
ordinal: 56000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

TASK-51の計測では、追跡ファイル20件・計40 MBの作業ツリーでrestoreに約1.2秒、statusに約0.4秒かかった。未保存の変更の判定で、変更のないファイルも毎回全体をハッシュ計算していることが主な原因である。GUI刷新後は移動のたびに判定が走るため、応答速度に直接影響する。

## ゴール

前回ハッシュ計算したときのサイズ・更新日時などを記録し、変わっていないファイルのハッシュ計算を省略する。内容が変わったのに検出できない状態を作らないことを最優先とする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 サイズ・更新日時などが前回の計算時と一致する追跡ファイルは、未保存変更の判定でハッシュを再計算しない
- [ ] #2 内容が変更されたファイルは、更新日時の粒度や同一秒内の書き換えを含めて変更として検出される
- [ ] #3 記録が欠落・破損・不一致の場合は全体のハッシュ計算へ安全に戻る
- [ ] #4 status、restore、switch、move、commitの結果が高速化前と一致する
- [ ] #5 TASK-51と同じ条件で、変更のない作業ツリーに対するstatusとrestoreの所要時間の改善が計測・記録される
- [ ] #6 変更検出の境界条件と記録の破損時の動作がテストされる
<!-- AC:END -->
