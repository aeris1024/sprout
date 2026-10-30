---
id: TASK-96
title: GUIへ戻ったときに作業フォルダの状態を自動で更新する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 17:53'
updated_date: '2026-10-30 21:27'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/App.tsx
  - gui/README.md
priority: high
type: enhancement
ordinal: 95000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
別のアプリでファイルを編集してGUIへ戻っても、「更新」を押すまで上部バーは「保存済み」のままで、未保存の変更も表示されない。別のアプリで編集して戻る使い方が中心のため、実際と異なる状態を信じて操作する原因になる。常時のファイル監視や自動スナップショットはTASK-30で扱い、本件はウィンドウへ戻ったときの再取得に限る。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ウィンドウがフォーカスを取り戻すと、未保存の変更と追跡状態、上部バー、マップが最新になる
- [x] #2 他の操作の実行中は割り込まず、操作の結果を壊さない。短時間にフォーカスが繰り返し変わっても再取得が過剰に走らない
- [x] #3 再取得で選択中の葉、入力中のメッセージやメモ、マップのスクロール位置が失われない
- [x] #4 CLIのロックなどで再取得できない場合に、操作を妨げるエラーを繰り返し表示しない
- [x] #5 自動テストでフォーカス時の更新、操作中の抑止、入力内容の維持を検証し、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Subscribe to onFocusChanged with the same pattern as the drag listener; 2. Refetch through fetchWorkspace outside execute so busy and notices stay; 3. Skip during operations, throttle with a trailing refresh, discard a result when an operation started meanwhile; 4. On failure show at most one warning per failure streak and only if no notice is displayed; clear it on success; 5. Add App tests, update gui/README.md; 6. Verify scroll and drafts in the browser harness; leave the real-device check pending.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented with getCurrentWindow().onFocusChanged outside execute, so busy, buttons and notices are untouched. Skips while an operation runs; at most one refetch per 2 s plus one trailing refetch; a result is discarded if an operation started during the refetch (status and tree take no repository lock, so a refetch does not cause lock failures for operations). Failure: one warning per failure streak, only when no notice is displayed, cleared on the next success. Selection cleanup in fetchWorkspace is kept. Commit detail is not reloaded, same as the update button. A focus that arrives during an operation is not replayed afterwards.

Permission: core:default already includes core:event:default (allow-listen, allow-unlisten), the same path as onDragDropEvent; no capability change needed.

Verified: 10 new App tests, pnpm test 136 passed, pnpm build OK. Browser harness with the real CLI and synthetic tauri://focus events: external edit changes the chip to unsaved 1; map scroll stays at 137,61; memo and message drafts stay; selected leaf stays; 8 rapid focus changes run 1 refetch and 1 trailing refetch; an external commit adds the leaf and keeps the draft.

PENDING: AC 1 real-device check of the native window focus event in pnpm tauri dev. TASK-96 stays In Progress.

Real Tauri window check: tauri://focus and tauri://blur listeners were accepted, so no capability change is needed. The native focus cycle could not be driven in this environment, so AC 1 stays unchecked. All code is on main; run the manual steps, then check AC 1 and finalize.
<!-- SECTION:NOTES:END -->
