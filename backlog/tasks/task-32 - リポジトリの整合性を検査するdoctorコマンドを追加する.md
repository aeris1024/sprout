---
id: TASK-32
title: リポジトリの整合性を検査するdoctorコマンドを追加する
status: To Do
assignee: []
created_date: '2026-07-20 10:18'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: medium
type: feature
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

外付けディスクやバックアップ運用では、objects の欠落・破損、DB参照との不一致、異常終了後のロック残骸などに気付きにくい。壊れてから restore で初めて分かるのは遅い。

## ゴール

リポジトリを読み取り検査し、問題があれば分かりやすく報告する `doctor`（名称は実装時に決めてよい）を追加する。原則として修復より検出を優先する。スキーマ変更は行わない。

## 検査したい観点（例）

- commit_files が指す object が実在するか
- object の内容ハッシュがファイル名と一致するか
- 必要なら古いロックや明らかに不整合な状態の指摘

破壊的な自動修復は必須としない。行う場合は明示オプションと確認可能な出力にする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 参照されているオブジェクトの欠落や破損を検出して報告できる
- [ ] #2 問題がないリポジトリでは成功として分かる結果になる
- [ ] #3 検査は作業ツリーや追跡状態を変更しない
- [ ] #4 READMEに使い方が追記されている
- [ ] #5 欠落・破損・正常系がテストで検証されている
<!-- AC:END -->
