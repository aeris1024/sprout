---
id: TASK-125.12
title: サムネイル個別操作とサムネイル自動生成元をleaf thumbnailへ統合する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-31 07:33'
updated_date: '2026-10-31 16:00'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
  - TASK-125.3
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - gui/src/App.tsx
  - gui/src-tauri/src/lib.rs
  - tests/test_cli.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 136000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在のthumbnailとcoverをleaf thumbnail配下へ統合する。個別の葉の確認・登録・変更・削除・取り出しと、自動生成元となる追跡画像の確認・指定・解除・既存葉への適用を同じ体系から操作する。file coverを正規の別入口として追加しない。
用語はユーザー確認済みの「サムネイル自動生成元」を用い、「代表ファイル」「代表にする」という現行の画面・ヘルプ上の名前を改める。自動生成そのものは維持し、CLIの具体的な下位構文は着手時に整える。
個別サムネイルは葉ごとのデータで、追跡対象外やプロジェクト外の画像も直接登録できる。サムネイル自動生成元は追跡ファイルを素材IDで指定するプロジェクト単位の設定。この区別を画面・ヘルプで明確にする。
commit/leaf createでの明示画像と自動生成の優先順位、既存葉へ適用するapply、生成できない場合の扱いを維持する。代表プレビューはTASK-125.14で廃止するが、サムネイルとプレビューの区別、プレビューの置き換えは維持する。素材関連付け廃止とプレビューの表示名・説明・順序の維持はTASK-125.13へ委ねる。ラベル維持・一覧・候補表示はTASK-125.15・TASK-125.16で確定済み。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 leaf thumbnailで葉ごとのshow/set/delete/exportと、自動生成元のshow/set/clear/apply相当を利用でき、独立したfile cover正規入口を不要にする
- [x] #2 個別画像に必要なLEAF指定と、プロジェクト単位の生成元設定の対象範囲をヘルプ・引数で判別できる
- [x] #3 leaf create時の明示画像と生成元の優先順位、生成できない場合の既存処理、画像の制約と原本を変更しない動作を維持する
- [x] #4 既存葉への適用は登録済みサムネイルを保持し、dry-runで変更せず対象を確認できる。取り出しの既存上書き確認とJSON契約も維持する
- [x] #5 生成元の素材ID・追跡解除・改名移動の扱いを維持し、GUIとRust側の取得を統合後の正規入口へ移行できる
- [x] #6 GUI・通知・CLIヘルプ・エラー表示・READMEでは自動生成元を「サムネイル自動生成元」と呼び、自動生成の機能は維持する
- [x] #7 直接のサムネイル登録に追跡条件を追加せず、追跡対象外・プロジェクト外の対応画像の登録と、追跡ファイルを使う自動生成元設定の違いを説明する
- [x] #8 代表指定廃止はTASK-125.14、素材関連付け廃止と表示名・説明・順序の維持はTASK-125.13と整合させ、ラベル維持・一覧・候補と新構文・失敗時の無変更・serveを検証してV1方針を維持する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Expose leaf thumbnail show/set/delete/export and source show/set/clear/apply by reusing existing image/recovery/safety callbacks. Keep temporary thumbnail/cover callers until GUI migration. Rename GUI/notifications/docs to サムネイル自動生成元, clearly distinguishing externally registered leaf thumbnails from tracked project source. Verify canonical source priority/identity/apply/dry-run and direct image/export safety plus existing16-bit regression, GUI tests/type/build. Keep V1 unchanged.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Canonical leaf thumbnail show/set/delete/export and source show/set/clear/apply reuse existing image and source operations; direct registration accepts outside/untracked images while source requires tracked identity. Renamed GUI/help/errors/docs to thumbnail source / サムネイル自動生成元, preserving stable cover JSON keys. Backend thumbnail/cover/serve52 passed; GUI245 passed, tsc and Vite build passed after updating obsolete marker assertion to生成元. Tests cover priority, historical dry-run/apply, identity across move/untrack, safe export and invalid-source handling; existing16-bit tests retained. V1 unchanged.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Unified individual thumbnails and project automatic generation under leaf thumbnail/source, clarified scope and renamed GUI source terminology. Verified52 backend tests,245 GUI tests, typecheck and production build; temporary old callers retained until migration cleanup.
<!-- SECTION:FINAL_SUMMARY:END -->
