---
id: TASK-84
title: previewに表示名・説明・代表指定と対象素材との関連付けを追加する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-29T20:09:00Z'
updated_date: '2026-10-30 15:57'
labels: []
dependencies:
  - TASK-83
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - src/sprout/archive.py
  - gui/src/components/PreviewPanel.tsx
  - gui/src/components/CommitPanel.tsx
  - tests/test_previews.py
  - gui/README.md
priority: medium
type: feature
ordinal: 83000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在のpreviewはコミット全体への添付で、元ファイル名・形式・表示順だけでは、どの素材のどの確認用ファイルなのかが分かりにくい。画像・音声・モデル等の複数添付を整理できるよう、原本のファイル名とは別の表示名と説明、コミットの代表preview、対象素材との関連付けを持たせる。関連付けはTASK-83の不変file_idを利用し、素材の改名・移動後も同一性を保つ。サムネイル画像の生成や自動置換、音声・動画・3D表示機能は本件に含めない。保存形式の変更はTASK-80に従う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 previewごとに表示名と説明を設定・編集・解除でき、元ファイル名・添付ID・原本の内容とは独立して保持する。未設定時の表示、文字数・改行などの規則が明確である
- [x] #2 コミットごとに代表previewを最大1件指定・変更・解除でき、GUIで識別できる。同じコミットに属するpreviewだけを指定でき、未指定時の表示が明確である
- [x] #3 previewをそのコミット内の対象素材へfile_idで関連付け・解除でき、GUIから対象を確認できる。複数素材への対応範囲を定義し、改名・移動や同名の別素材で関連を混同しない
- [x] #4 previewの置き換え・並べ替え・削除、素材の削除、葉の削除/取り消し時の表示名・説明・代表指定・素材参照の扱いを定義し、無効な参照を残さない。代表指定でサムネイルの原本や未選択メディアの自動読み込みを変更しない
- [x] #5 CLI・JSON・GUIからメタ情報を確認・更新でき、archiveにも保存する。失敗した更新は既存の添付内容・順序・関連情報を部分的に変更しない
- [x] #6 未設定、設定・解除、他コミットや存在しない添付/素材の指定、改名・移動、置換・削除・取り消し、再オープンと更新失敗を自動テストで検証し、READMEを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Pending combined policy review with TASK-83/85. After TASK-83 is complete, use schema V7 for optional NFC display name (256 characters, no newlines), multiline description (20000 characters), at most one explicit representative preview per commit, and many-to-many links to file IDs present in that commit. Preserve metadata/links/representative state on content replacement; remove on deletion and recover through trash with atomic conflict checks. Unset display name falls back to original filename; no representative fallback or automatic media decoding. Expose editing/inspection in CLI/JSON/GUI and archive. Test identity, cross-commit invalid references, replacement/order/delete/undo, re-open and failed updates; finalize and integrate independently before TASK-85.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Combined policy approved by user. TASK-83 is complete and integrated; implement the approved preview metadata, representative and multiple file-ID associations next.

Implemented approved V7 preview display_name/description, one representative per commit, and multiple immutable file-ID associations constrained to the same snapshot. CLI metadata command, JSON, GUI editing/badges/material paths and static archive metadata/rendering are connected; unset names fall back to original names, and representative changes do not decode media or alter thumbnails. Content replacement retains metadata and links. Trash record Version 2 captures associations and restores them atomically with original attachment rows; later metadata/link edits reject older recovery. Frozen V6 fixture and compatibility guards added. Validation: full Python run 499 passed, 19 skipped and one missing composite FK index; added that index and relevant suite 133 passed. Additional malformed recovery-context checks plus metadata/trash tests 33 passed. GUI full 108 passed; TypeScript noEmit and diff check passed. New metadata coverage includes normalization/limits, set/clear, primary uniqueness, multiple/cross-commit references, rename identity, replace/delete/commit undo, archive/reopen and atomic failures.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Add preview presentation metadata, representative selection and multiple same-snapshot material links through CLI/JSON/GUI/archive. Preserve metadata and associations across content replacement and atomic trash recovery, reject invalid or conflicting references, and introduce schema V7 plus recovery record Version 2. Verified full regression run with composite-index repair and 133/33 focused tests, 108 GUI tests and type checks.
<!-- SECTION:FINAL_SUMMARY:END -->
