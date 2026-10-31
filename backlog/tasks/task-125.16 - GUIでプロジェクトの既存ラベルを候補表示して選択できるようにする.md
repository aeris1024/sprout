---
id: TASK-125.16
title: GUIでプロジェクトの既存ラベルを候補表示して選択できるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-31 08:55'
updated_date: '2026-10-31 15:59'
labels:
  - gui
  - labels
dependencies:
  - TASK-125.15
references:
  - gui/src/components/CommitAnnotations.tsx
  - gui/src/App.tsx
  - gui/src/lib/sprout.ts
  - gui/src/App.test.tsx
  - gui/README.md
parent_task_id: TASK-125
priority: medium
type: feature
ordinal: 140000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ラベルを残す方針に合わせ、GUIでラベルを付けるとき、プロジェクト全体で使用中のラベルから候補を選べるようにする。ラベル名を毎回思い出して入力する負担と表記の揺れを減らす。候補の取得元はCLIのプロジェクト全体一覧とし、GUIがDBを直接参照しない。
入力が空でも既存ラベル一覧と利用中の葉数を確認でき、入力に応じて絞り込み、選択して現在の葉へ追加できる。候補にない新しいラベルも従来どおり入力して追加できる。現在の葉に既に付いているラベルの重複追加を防ぐ。独立したラベル辞書や管理画面を増やすことは要件にしない。
プロジェクト・葉の切り替え、追加/解除・削除/復旧後に古い候補や対象葉を誤って使わない。既存のラベル解除、マップのメッセージ/タグ/ラベル検索は維持する。専用ラベル検索UIの追加や高度なAND/OR検索は含めない。今回の依頼はBacklogへの登録のみ。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ラベル入力欄からプロジェクト全体の既存ラベルと利用中の葉数を確認でき、空入力時の全候補表示と入力による絞り込みができる
- [x] #2 候補を選んで表示中の葉へ付けられ、候補にない新規ラベルの入力・追加と既存ラベルの解除も利用できる
- [x] #3 既に付いているラベルを重複追加せず、キーボードとマウスで候補の選択・確定・キャンセルができ、入力中に勝手に付与しない
- [x] #4 プロジェクトや葉の切り替えとラベル変更・葉の削除/復旧後の更新で、別プロジェクトの候補や古い対象葉への追加が起きない
- [x] #5 候補なし・読み込み中・取得失敗を判別でき、候補取得が失敗しても既存のラベルや入力を失わず、新規入力と再試行を利用できる
- [x] #6 GUIは正規CLI/JSONを使い、候補選択・新規追加・重複・対象切り替え・失敗時を検証し、既存のマップ検索を維持してGUI READMEを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Add a lazy project-label candidate input using canonical leaf label list JSON, with counts/filtering, keyboard/pointer confirmation and explicit loading/empty/error/retry states. Keep free-text additions and removals, prevent duplicates, scope async requests and drafts to project/leaf, refresh after edits, consume Escape locally. Verify component races and App canonical calls plus GUI tests/type/build; update README.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented project/leaf-scoped LabelInput using canonical leaf label list JSON plus canonical add/remove. Empty focus lists labels and counts; typing filters; explicit mouse/keyboard confirmation, NFC duplicate guard, pending-add guard, local Escape preserving draft, loading/empty/error/retry and free-text fallback. Context remount ignores old project/leaf requests; labels/busy changes invalidate candidates so edits/deletion/recovery are fetched fresh on next use. README updated. Validation: all256 GUI tests passed, including9 candidate component tests and App canonical CLI integration; TypeScript and Vite production build passed; diffcheck clean.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Offer existing project labels and usage counts while preserving new-label input and removal. Prevent duplicate or stale-target additions and retain input through candidate failures. Verified256 GUI tests, type checking and production build; README updated.
<!-- SECTION:FINAL_SUMMARY:END -->
