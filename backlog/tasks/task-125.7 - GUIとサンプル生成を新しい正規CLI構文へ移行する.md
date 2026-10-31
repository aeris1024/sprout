---
id: TASK-125.7
title: GUIとサンプル生成を新しい正規CLI構文へ移行する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-31 07:24'
updated_date: '2026-10-31 16:24'
labels:
  - cli
  - gui
  - usability
dependencies:
  - TASK-125.1
  - TASK-125.2
  - TASK-125.3
  - TASK-125.4
  - TASK-125.5
  - TASK-125.9
  - TASK-125.10
  - TASK-125.11
  - TASK-125.12
  - TASK-125.14
  - TASK-125.16
  - TASK-125.13
references:
  - gui/src/App.tsx
  - gui/src/components/PreviewImage.tsx
  - gui/src/components/ComparePanel.tsx
  - gui/src-tauri/src/lib.rs
  - scripts/create_sample_repo.py
  - gui/src/App.test.tsx
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 131000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CLI再編に合わせてGUIと同梱スクリプトの呼び出しを正規構文へ統一する。GUIは手打ちaliasへ依存せずleaf/bud/branch/file/maintenance等を使う。
対象はAppや各パネル、プレビュー画像取得、Rust側のサムネイル取得とCLI/serve呼び出し、サンプルリポジトリ生成など実際の全利用箇所。GUIの表示用語や機能を増やすタスクではない。別途存在するTASK-88/89/90/91/121等のGUI機能追加とは範囲を分ける。
追補: go系・log系・message系・thumbnail系の操作統合後の正規構文を使う。特に移動、メモ編集、サムネイル生成元は旧案のbranch switch/leaf restore/leaf note/file coverへ移行しない。previewの代表指定はTASK-125.14で廃止し、順序と置き換えを維持する。GUI・サンプルの代表指定呼び出しや表示は廃止後の契約へ合わせる。「代表ファイル」は「サムネイル自動生成元」に改称する。ラベル維持・全体一覧と候補表示はTASK-125.15・TASK-125.16で実装し、その正規CLI/JSONをGUIから利用する。プレビューは葉全体の確認資料とし、TASK-125.13で素材関連付けを廃止する。GUIとサンプルから対象素材の表示・選択・関連指定を除き、表示名・説明・順序・置き換えを維持する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 決定済みのGUIの保存・履歴・詳細・分岐・移動・退避・部分復元・取り出し・説明編集・タグ・サムネイル・生成元・ゴミ箱・保守を統合後の正規構文で呼び出す
- [x] #2 Rust側のサムネイル取得と常駐モードを含め、都度起動とserve経由の両方で操作・エラー通知・画像表示が従来どおり動作する
- [x] #3 サンプル生成など同梱スクリプトの実コマンド呼び出しを移行し、生成される履歴・タグ・添付・つぼみ・ゴミ箱の内容を維持する
- [x] #4 GUIのテストが新しい正規argvを検証し、GUIのテスト・型チェック・ビルドと該当Rustテストが成功する
- [x] #5 ラベル維持・一覧/候補と整合させ、代表指定と素材関連付けの廃止・表示名/説明/順序/置き換えの維持・サムネイル自動生成元の名称をGUI/サンプルへ反映する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Migrate all GUI, Rust thumbnail and sample-generator call sites to canonical nested CLI argv while preserving existing behavior and JSON/serve handling. Align GUI tests and sample guide; validate nested Rust argv and nullable go results. Run GUI suite/type/build, Rust lib tests with shared target cache and sample-repository tests using the worktree source.

Preserve option-like user text during migration: positional separators, equals-form option values, and JSON insertion before separators in Rust. Verify leading-dash comments and names plus literal --json labels/messages/notes through GUI, Rust and actual CLI.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated App, comparison/preview components, Rust thumbnail export argv, sample generator and sample guide to canonical CLI; no GUI operation depends on hand-typing aliases. Branch creation now uses branch create NAME LEAF --switch with default bud protection; nullable go JSON already supported. Label candidates, simplified preview metadata and source terminology retained. Added Rust nested thumbnail argv assertion and a real external serve sample integration comparing canonical GUI reads to one-shot CLI plus exporting thumbnail PNG. Validation: all256 GUI tests passed; TypeScript/Vite build passed; cargo test --lib8passed; sample repository5tests passed with worktree PYTHONPATH; diffcheck clean.

Pre-merge review found option-like positional text and literal --json values could be reinterpreted after migration. Reopened affected acceptance checks for the fix and focused round-trip verification before committing.

Resolved pre-merge text regression: conditional positional separators preserve leading-dash branch/tag comments, bud/branch renames and arbitrary labels; equals-form message/note/comment options preserve literal --json values. Rust adds its actual JSON flag before the positional separator and does not confuse a --json label with the flag. Added6 App edge tests,1Rust JSON-boundary test and actual CLI round trips covering dash/newline comments, bud name, --json note/message/label and domain rejection of invalid branch names. Latest validation supersedes earlier counts: all262 GUI tests passed; TypeScript/Vite build passed; Rust9passed; sample/serve5passed plus text roundtrip1passed separately; diffcheck clean.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Migrate GUI, native thumbnail reads and sample generation/guide to canonical CLI, preserving option-like free text and JSON boundaries. Verified262 GUI tests, type/build checks,9Rust tests and6sample/text integration cases, including real serve/one-shot parity and thumbnail export.
<!-- SECTION:FINAL_SUMMARY:END -->
