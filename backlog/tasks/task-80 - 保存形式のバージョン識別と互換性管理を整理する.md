---
id: TASK-80
title: 保存形式のバージョン識別と互換性管理を整理する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-29T19:06:00Z'
updated_date: '2026-10-30 14:29'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - README.md
  - tests/test_v1_storage.py
  - tests/test_restore_safety.py
priority: high
type: enhancement
ordinal: 79000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現行の保存形式はSchema Version 1だが、開発中の異なる構造にも同じ番号が使われ、SQL定義の照合で区別している。これから更新日時の保存単位や削除復旧の構造を変更する前に、形式番号と対応構造の関係、互換性判定、運用開始前後の移行方針を明確にする。現時点ではアプリは未運用のため、開発用DBの自動移行は作らず、非対応形式を非変更で拒否して退避・再初期化を案内する方針とする。今後の運用データ向け移行機構の実装や、更新日時・取り消し機能そのものは別タスクで扱う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 保存形式の番号と対応構造が一意に対応し、新しい非互換形式にはV2以降の増加する番号を割り当てる。同じV1番号へ異なる新構造を追加しない
- [x] #2 現行開発用V1・過去の開発用形式・未知の新しい番号・必須構造の欠落に対する読み書き可否を定義し、非対応形式はDB・objects・作業ファイルを変更せず拒否する
- [x] #3 アプリのバージョン、DBの形式番号、objectsのencoding、復元操作記録のバージョンそれぞれの互換性判断と、非対応状態での処理を文書化する。DB番号だけでencodingや復旧記録を対応済みと判断しない
- [x] #4 開発用DBは必要データを退避した上で再初期化する手順を示し、自動変換・自動修復は行わない。運用開始後の非互換変更に対する移行方針も明記する
- [x] #5 新規初期化、対応形式の再オープン、同番号の不正構造、未知の形式番号、非対応encoding・復元記録の拒否を自動テストで検証し、CLI・JSON・GUIで対応できない理由を確認できる
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Preserve the current V1 layout and freeze its identity; add structured compatibility errors and nonmutating rejection tests; document version policy, backup/reinitialization and future migrations; verify CLI/JSON/GUI errors and run the full test suite.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Preserved the V1 schema and added a frozen-definition regression check. Added structured format/recovery errors and read-only recovery preflight. Documented independent version checks, development backup/reinitialization, and future explicit migration requirements. Verification: full Python run had 415 passed, 19 skipped and 21 assertions for the old error wording; updated those expectations and reran all repository tests (142 passed, 2 skipped), yielding 436 passed and 19 skipped across the suite. GUI App/error tests: 68 passed. TypeScript noEmit and git diff --check passed. Windows junction tests were run outside the sandbox after sandbox permission failures.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Freeze current V1 identity and require increasing format numbers for incompatible changes. Reject unsupported DB/recovery formats with actionable structured errors before mutations. Add backup/reinitialization and future migration policy, plus CLI/JSON/GUI regression coverage. Verified Python suite with repository rerun, 68 GUI tests, and TypeScript checks.
<!-- SECTION:FINAL_SUMMARY:END -->
