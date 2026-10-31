---
id: TASK-125.15
title: プロジェクト全体のラベル一覧をCLI・JSONで取得できるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-31 08:55'
updated_date: '2026-10-31 11:23'
labels:
  - cli
  - labels
dependencies:
  - TASK-125.1
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - src/sprout/serve.py
  - tests/test_cli.py
  - tests/test_repository.py
parent_task_id: TASK-125
priority: medium
type: feature
ordinal: 139000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ユーザーはラベル機能を残す方針を確定した。ラベルを葉全体に付く再利用可能な分類として維持し、現在の葉ごとの一覧・追加・解除と履歴のラベル検索に加えて、プロジェクト全体で現在使われているラベル一覧を取得できるようにする。
対象は全ブランチの現存する葉（ブランチ削除後も履歴に残る葉を含む）に付いたラベル。ゴミ箱にしか残っていない付与や別プロジェクトは候補に含めず、同じラベルを重複なく集計する。ラベルごとの利用中の葉数も確認でき、最後の付与を外せば一覧から消え、復旧して現存する葉へ戻れば再び集計される。
既存の付与情報から取得し、専用の永続ラベル辞書を追加する必要はない。V1保存形式と現在のNFC正規化・前後空白除去・大文字小文字を区別する同一性を維持する。CLIはleaf体系の中でプロジェクト全体一覧と葉ごとの確認・追加・解除を混同せず使えるようにする。具体的な下位構文は着手時にCLI再編と整合させる。
Git式のタグ参照やpruneの保護対象へ変える機能ではなく、複数条件の高度なラベル検索やCLIのラベルTab補完の追加も今回の範囲外。今回の依頼はBacklogへの登録のみ。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 プロジェクト全体の使用中ラベルを、全ブランチとブランチ削除後の現存履歴から重複なく一覧取得でき、ラベル名と利用中の葉数を確認できる
- [x] #2 ゴミ箱にしかない付与・他プロジェクトのラベルを含めず、追加・解除・葉の削除・復旧後に現在の状態へ更新される。使用中ラベルがなければ空の一覧を返す
- [x] #3 CLIとJSONで一覧を取得でき、葉ごとの既存ラベル確認・追加・解除や、leaf listへの統合後も既存のラベル絞り込みを維持する
- [x] #4 ラベルの既存の同一性・正規化・文字数と件数制約を維持し、並び順を安定させ、同じ葉の同じラベルを重複計数しない
- [x] #5 V1保存形式を変えずラベル辞書の新規永続化を必要とせず、読み取りの一覧取得で葉・作業ファイル・付与情報を変更しない
- [x] #6 空の一覧・複数ブランチ・同名ラベル・大文字小文字・正規化・削除/復旧・JSON・serveを検証し、ヘルプとREADMEを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Add read-only project label aggregation from existing live leaf labels; expose leaf label list [LEAF], add LEAF LABEL and remove LEAF LABEL with old temporary callers retained. Verify branch scopes, normalization/case, dedup counts, deletion/restoration and JSON/serve contracts plus V1/read-only state. Document canonical syntax.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Canonical syntax: leaf label list [LEAF], add LEAF LABEL, remove LEAF LABEL. Global JSON is [{name,leaf_count}]; explicit LEAF returns existing annotations. Read-only SQL aggregates existing labels on live leaves including deleted-branch origin, excluding trash-only and other projects. No schema or dictionary added. Old label caller remains temporary until125.8. Validation: new project-label/group/serve tests22passed; label-specific repository/CLI regressions13passed (overlapping new tests). Tests cover NFC, case, distinct counts, last removal, leaf deletion/restoration, read-only V1 state and JSON Lines. README/help updated; diffcheck clean.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Expose project-wide label names and leaf counts plus canonical per-leaf label operations without changing V1 storage. Verified scope, normalization, deletion/recovery, read-only state and CLI/JSON/serve with22 focused tests and13 label regressions; README updated.
<!-- SECTION:FINAL_SUMMARY:END -->
