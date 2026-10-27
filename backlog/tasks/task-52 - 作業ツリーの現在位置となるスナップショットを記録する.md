---
id: TASK-52
title: 作業ツリーの現在位置となるスナップショットを記録する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-27 15:03'
updated_date: '2026-10-27 15:30'
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
- [x] #1 全体restore、switch、branch --switch、commitの成功後に現在位置が対象スナップショットへ更新される
- [x] #2 部分restoreや失敗・中断した操作では現在位置が変わらないか、操作前の値へ復旧される
- [x] #3 statusとtreeのJSON出力に現在位置のコミットIDと、それが現在ブランチの先端かどうかが含まれ、人向けstatusにも先端以外を表示中であることが示される
- [x] #4 コミットがない新規リポジトリでは現在位置が空として扱われる
- [x] #5 ブランチ先端以外を表示中に起点省略のブランチ作成を拒否する既存の保護が、記録した現在位置に基づいて動作する
- [x] #6 pruneやブランチ削除で現在位置のコミットが失われない、または失われる操作が拒否される
- [x] #7 READMEとJSON契約が更新され、各操作での現在位置の更新と非更新がテストされる
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. metaに現在位置キーcurrent_commitを追加し、init時は空で作成する。既存リポジトリでの扱いはユーザー判断（必須化して再初期化を求めるか、欠落時はブランチ先端とみなすか）。
2. Repositoryにcurrent_commit()と、現在ブランチ先端かを返す判定を追加する。
3. 全体restore・switch・branch --switchは_finalize_materializationで、作業ツリー確定と同じDBトランザクション内で現在位置を書き込む。部分restoreは更新しない。失敗・中断時はロールバックでDBを変更しないため現在位置は操作前のまま残る。
4. commitはブランチ先端の更新と同じトランザクションで現在位置を新コミットにする（途中からの保存の親の変更はTASK-55で扱う）。
5. 起点省略のブランチ作成の拒否を、ファイル内容の一致による推測から記録した現在位置に基づく判定へ置き換える。
6. pruneは現在位置のコミットを保護対象に加える。ブランチ削除はコミットを消さないため変更不要。doctorは現在位置が存在しないコミットを指す場合を問題として報告する。
7. status（パス指定時を含む）とtreeのJSONにcurrent_commitとat_branch_tipを追加し、人向けstatusは先端以外を表示中であることを表示、人向けtreeは現在位置に印を付ける。
8. README・JSON契約を更新し、各操作での更新・非更新、中断復旧、新規リポジトリ、prune保護、ブランチ作成拒否のテストを追加して全テストを通す。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
既存リポジトリの扱い（2026-10-28 ユーザー決定）: metaにcurrent_commitがない既存リポジトリは、現在ブランチの先端にいるものとみなしてそのまま使えるようにする。current_commitは必須メタデータにせず、初回の全体restore・switch・commitなどで書き込む。

## 実装と検証（2026-10-28）
- metaのcurrent_commitに現在位置を保存。値がない・空の場合は現在ブランチ先端とみなす（既存リポジトリ互換）。必須メタデータにはしていない。
- 全体restore・switch・branch --switchは_finalize_materializationで作業ツリー確定と同じDBトランザクション内に書き込み、commitはブランチ先端更新と同じトランザクションで更新。部分restoreは更新しない。失敗・中断時はロールバックがDBを変えないため操作前の値が残る。
- 起点省略のブランチ作成拒否を、ファイル内容の一致による推測から記録した現在位置に基づく判定へ置換し、不要になった_working_content_signatureを削除。
- pruneは現在位置を保護対象に追加（既存の内容一致による拒否は部分restore等のために維持）。doctorは存在しないコミットを指す現在位置をmissing_current_commitとして報告。
- status（パス指定含む）とtreeのJSONにcurrent_commitとat_branch_tipを追加。人向けstatusは先端以外でViewing saved snapshot行、treeはcurrent印を表示。README更新。
- 既存テストの契約変更: tree空リポジトリとstatusのJSON期待値に新フィールドを追加。prune拒否テストは、現在位置を保護する新テストと、部分restoreで内容が一致する場合の拒否テストに分割。
- 検証: uv --cache-dir .uv-cache run --frozen pytest -q -p no:cacheprovider --basetemp .test-tmp/task52 で229 passed, 19 skipped（スキップはWindowsのsymlink権限等の環境条件）。別プロセスのCLIでinit・track・commit・restore・status・status --json・tree・branch拒否・doctor・restore mainを確認。git diff --check成功。
- 気づいた点（範囲外）: statusのchangesは現在位置ではなくブランチ先端と比較するため、先端以外へ移動した直後もmodifiedと表示される。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
作業ツリーの現在位置をmetaのcurrent_commitとして記録し、全体restore・switch・branch --switch・commitで作業ツリー確定と同じトランザクション内で更新するようにした。記録がない既存リポジトリはブランチ先端とみなす。status・treeのJSONにcurrent_commitとat_branch_tipを追加し、人向け表示も対応。起点省略のブランチ作成拒否を記録した現在位置に基づく判定へ置き換え、pruneで現在位置を保護し、doctorで不整合を検出する。全229テスト成功（19件は環境条件でスキップ）と別プロセスCLIの動作確認で検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
