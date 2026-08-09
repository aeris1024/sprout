---
id: TASK-47
title: GUIのフォーカス更新とサムネイル登録競合を修正する
status: Done
assignee:
  - '@codex'
created_date: '2026-08-09 09:07'
updated_date: '2026-08-09 09:21'
labels: []
dependencies: []
references:
  - gui/src/App.tsx
  - gui/src/App.test.tsx
priority: high
type: bug
ordinal: 47000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUIがwindow focusのたびにワークスペース全体を再取得するため、Windowsの移動・サイズ変更でも過剰な更新が発生する。また、ネイティブ画像選択ダイアログ終了時のfocus更新が先に開始されると、operationActiveにより過去コミットへのサムネイル登録が無言で破棄される。外部変更の同期を手動更新に限定し、GUI操作後の同期は維持して競合を解消する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ウィンドウのfocusイベント、移動、サイズ変更だけではstatus・log・branch・treeの再取得が発生しない
- [x] #2 更新ボタンを押すとワークスペース全体が再取得され、外部変更が表示される
- [x] #3 コミット、追跡、復元、ブランチ、サムネイル登録などGUI操作完了後の状態再取得は維持される
- [x] #4 過去コミットの画像選択中にfocusイベントが発生してもサムネイル登録が実行され、ツリーと詳細に反映される
- [x] #5 focus非更新、手動更新、ダイアログ競合、既存GUI操作が自動テストで検証される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. window focusによる自動refresh effectを削除し、手動更新とGUI操作後のfetchWorkspaceだけを残す。 2. focusイベントが更新を起こさないこと、更新ボタンが再取得すること、画像ダイアログ中のfocus後も過去コミットへのthumbnail操作が完了することをReactテストで検証する。 3. Vitest全件、TypeScript型検査、GUIビルドと使い捨てSproutTestコピーでのTauri手動確認を行う。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
window.focusの自動更新を削除。外部変更は更新ボタン、GUI操作完了後は既存の再取得を維持した。Vitest 22件、tsc --noEmit、Vite buildが成功。TauriでSproutTestの使い捨てコピーを開き、移動・サイズ変更後も応答を確認。再起動後のGUI自動操作環境が不安定だったため、画像ダイアログ競合はfocusイベントを挟むReactテストとコピー上のCLI tree確認で検証した。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Removed focus-triggered workspace refresh to prevent excessive GUI updates and native dialog races. Verified manual refresh and past-commit thumbnail registration with 22 passing Vitest tests, TypeScript type checking, production build, and a disposable Tauri project check.
<!-- SECTION:FINAL_SUMMARY:END -->
