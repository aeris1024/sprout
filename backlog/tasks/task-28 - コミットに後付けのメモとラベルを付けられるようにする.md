---
id: TASK-28
title: コミットに後付けのメモとラベルを付けられるようにする
status: To Do
assignee: []
created_date: '2026-07-15 16:39'
updated_date: '2026-07-29 19:25'
labels: []
dependencies:
  - TASK-37
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: medium
type: feature
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

コミットメッセージは作成時に固定されるため、「提出した版」「ボツ」「クライアントOK」のような後から分かる情報を記録する場所がない。編集可能なメモとラベルがあると、GUIのツリービューでの絞り込み・色分け、CLI検索、静的アーカイブでの整理に利用できる。タグは不変の目印、メモとラベルは編集可能な注記として役割を分ける。

## 前提となる保存形式

TASK-37のSchema Version 3で用意されるcommit_notesとcommit_labelsを使用する。commit_notesはコミットごとに1件のnoteとupdated_atを持ち、commit_labelsはコミットごとに複数の重複しない自由文字列ラベルを持つ。

## 機能範囲

- コミットのメモを設定、上書き、削除できる
- コミットへラベルを追加、削除できる
- 空または空白だけのラベルは拒否する
- show、log、JSON出力でメモとラベルを確認できる
- logをラベルで絞り込める
- TASK-22のコミットグラフにメモとラベルを含め、GUIと静的アーカイブから利用できる
- 書き込み操作は他のリポジトリ更新と同様に排他制御する
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 コミットへのメモの設定、上書き、削除ができ、更新日時が正しく更新される
- [ ] #2 コミットへの複数ラベルの追加と削除ができ、同一ラベルが重複しない
- [ ] #3 空または空白だけのメモやラベルについて、定義された削除または拒否の挙動が一貫している
- [ ] #4 showとJSON出力でメモ、メモ更新日時、ラベルを確認できる
- [ ] #5 logを指定ラベルで絞り込める
- [ ] #6 TASK-22のコミットグラフ出力にメモとラベルが含まれる
- [ ] #7 READMEが更新され、メモとラベルの設定、変更、削除、検索、JSON出力が自動テストで検証される
<!-- AC:END -->
