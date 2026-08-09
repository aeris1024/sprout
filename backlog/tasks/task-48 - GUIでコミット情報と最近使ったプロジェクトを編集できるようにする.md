---
id: TASK-48
title: GUIでコミット情報と最近使ったプロジェクトを編集できるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-08-09 10:20'
updated_date: '2026-08-09 10:33'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - gui/src/App.tsx
  - gui/src/components/CommitTree.tsx
  - gui/src/lib/settings.ts
priority: medium
type: enhancement
ordinal: 48000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUI試用時に、Selected Commitからコミットメッセージを修正できず、最近使ったプロジェクト一覧から不要な項目を除外できない。また、削除済みブランチ由来のコミットが『削除済み』と表示され、コミット自体が削除されたように見える。コミット履歴の安全性を保ったまま編集操作を追加し、表示の意味を明確にする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Selected Commitから既存のコミットメッセージを編集・保存でき、保存後にツリー、履歴、選択中コミット詳細へ反映される
- [x] #2 CLIからコミット参照を指定してメッセージを変更でき、空のメッセージは拒否される
- [x] #3 メッセージ変更後もコミットID、親子関係、保存ファイル、添付、ブランチおよびタグの参照は変化しない
- [x] #4 最近使ったプロジェクトの各項目を履歴一覧から削除でき、プロジェクトのファイルやSprout履歴は削除されない
- [x] #5 現在開いているプロジェクトを最近使った一覧から削除しても表示中のプロジェクトは閉じず、再度開いた場合は一覧へ追加される
- [x] #6 削除済みブランチ由来の表示から、コミットは残っていて作成元ブランチだけが存在しないことを判別できる
- [x] #7 CLI、GUI、設定保存の自動テストと利用者向けドキュメントが更新される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Repositoryにschema変更なしのコミットメッセージ更新APIを追加し、CLIのmessageコマンドからコミット参照・新メッセージ・JSON出力を扱う。2. Selected Commitへ編集UIを追加し、保存後にworkspaceと選択詳細を再取得する。削除済みブランチの表示文言も由来が明確になるよう変更する。3. 最近使ったプロジェクトの純粋な削除ヘルパーと項目別削除UIを追加し、現在のプロジェクトを閉じずに設定だけ保存する。4. Repository/CLI/GUI/設定ヘルパーの回帰テストとREADMEを更新し、全テスト・型検査・ビルドで検証する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
schema変更なしでRepository.set_messageとmessage CLIを追加。Selected Commitの編集UIは成功時にtree、log、showを再取得し、失敗時は編集内容を維持する。最近使ったプロジェクトの削除はTauri Store設定だけを更新する。

Validation: pytest 142 passed/2 skipped、Vitest 25 passed、tsc --noEmit成功、Vite production build成功、git diff --check成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added safe commit-message editing across Repository, CLI, and Selected Commit; added recent-project list removal without touching project data; clarified deleted-branch provenance. Verified with complete Python and GUI suites, type checking, and production build.
<!-- SECTION:FINAL_SUMMARY:END -->
