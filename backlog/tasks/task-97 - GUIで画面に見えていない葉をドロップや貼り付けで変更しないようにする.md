---
id: TASK-97
title: GUIで画面に見えていない葉をドロップや貼り付けで変更しないようにする
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
  - gui/src/components/PreviewPanel.tsx
  - gui/README.md
priority: high
type: bug
ordinal: 96000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ファイルのドロップと画像の貼り付けの対象は、表示中のパネルではなく選択中の葉で決まる。ゴミ箱パネルを表示中でも、葉を選択していればドロップはその葉のプレビューに追加され、画像の貼り付けはサムネイルを確認なしで置き換える。テキスト入力欄で画像を貼り付けた場合も同様に置き換わる。コードの確認による判断で、実機での再現が必要。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ゴミ箱パネルなど葉の詳細以外を表示中は、ドロップと貼り付けで表示されていない葉を変更しない
- [x] #2 ドロップ中に、追加先が分かる表示が出る
- [x] #3 既存のサムネイルを貼り付けで置き換える前に、置き換えることが確認でき、取り消せる
- [x] #4 メモやメッセージなどのテキスト入力欄で画像を貼り付けても、意図せずサムネイルを変更しない
- [x] #5 自動テストで表示中のパネルごとの動作を検証し、実機でドロップと貼り付けを確認して、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Derive the displayed side panel in one place and use it for drops and pastes; 2. Track drag enter/over/leave to show a drop destination indicator; trash, compare and settings accept no drop; 3. Ignore image pastes in text fields, confirm before replacing an existing leaf thumbnail, keep save form paste and the preview paste area; 4. Add App tests per panel, update gui/README.md; 5. Leave the real-device check pending.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Drops and image pastes now use the displayed panel (order of sidePanel()). Commit detail: preview add. Files, save form, branch, bud: track. Trash, compare, settings and a not yet loaded leaf: no drop, with a hover message and a warning notice. Decisions: trash and compare no longer track a drop; CLI settings blocks drops and thumbnail pastes even though the side panel stays visible, because the request said settings must not change a leaf. Pasting over a draft save form thumbnail stays unconfirmed because it does not change a saved leaf. Image paste into a text field does nothing, with a warning only when the clipboard has no text. The drag listener now subscribes once and reads a ref, like the paste handler, so hover state is not lost on re-subscribe.

Verified: 16 new App tests, pnpm test 126 passed, pnpm build OK. Browser harness with the real CLI and synthetic Tauri drag events and ClipboardEvent: leaf hover names the leaf; leave clears it; trash drop and paste leave thumbnail hash and preview count unchanged; cancel keeps the hash; accept changes it; textarea paste keeps it; a drop on the leaf detail adds one preview; save form paste still works.

PENDING: AC 5 real-device check of native drag and drop and clipboard paste in pnpm tauri dev. Native events were not exercised, so TASK-97 stays In Progress.

Native drag and drop and OS clipboard paste could not be driven in this environment, so AC 5 stays unchecked. All code is on main; run the manual steps, then check AC 5 and finalize.
<!-- SECTION:NOTES:END -->
