---
id: TASK-61
title: statusなどの変更判定を作業ツリーの現在位置と比べるようにする
status: To Do
assignee: []
created_date: '2026-10-27 15:32'
updated_date: '2026-10-27 15:32'
labels:
  - cli
  - gui-redesign
dependencies:
  - TASK-52
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: medium
type: enhancement
ordinal: 61000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

TASK-52で作業ツリーの現在位置（基づいているスナップショット）を記録するようになった。しかし、statusの変更一覧、引数なしのdiff、未保存の変更の判定は、今も現在ブランチの先端と比べている。そのため、restoreで過去のスナップショットへ移動した直後は、何も編集していなくてもstatusにmodifiedなどが表示される。GUI刷新（doc-1）では、未保存の変更の有無が上部バーの表示、未保存の芽、つぼみへの自動退避の判断に直結するため、現在位置を基準にする必要がある。

## ゴール

作業ツリーの変更を判定する処理の比較相手を、ブランチ先端から現在位置へ変える。ブランチ先端にいる場合の結果は従来と変わらない。途中のスナップショットからの保存（commitの親や、変更がないときの扱い）はTASK-55で扱う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 過去のスナップショットへ全体restoreした直後、ファイルを編集していなければstatusの変更一覧が空になり、人向け表示はWorking tree cleanになる
- [ ] #2 現在位置からファイルを追加・変更・削除すると、statusにそれぞれadded・modified・deletedとして表示される
- [ ] #3 引数なしのdiffが、ブランチ先端ではなく現在位置と作業ツリーを比べる
- [ ] #4 restore・switch・branch --switchの未保存の変更の判定が現在位置を基準に行われ、現在位置から変更がなければ--discardなしで別のスナップショットへ移動できる
- [ ] #5 現在位置がブランチ先端のとき、および現在位置の記録がない既存リポジトリでは、status・diff・未保存の変更の判定の結果が従来と同じになる
- [ ] #6 statusのJSONとGUIが表示する変更件数が現在位置を基準にした値になり、READMEの説明が更新される
- [ ] #7 先端・過去のスナップショット・編集あり・編集なし・記録なしの各場合がテストされる
<!-- AC:END -->
