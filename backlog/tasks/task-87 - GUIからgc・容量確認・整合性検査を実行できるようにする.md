---
id: TASK-87
title: GUIからgc・容量確認・整合性検査を実行できるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 17:34'
updated_date: '2026-10-30 21:13'
labels:
  - gui
dependencies: []
references:
  - src/sprout/cli.py
  - gui/src/App.tsx
  - gui/README.md
priority: high
type: feature
ordinal: 86000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUIのゴミ箱で「完全削除」しても実体は次回の`sprout gc`まで回収されないが、GUIにはgcを実行する手段がなく、CLIを使わないと容量を空けられない。同じ保守操作である`sprout stats`と`sprout doctor`もGUIから使えない。3つのコマンドはTASK-46でJSON出力に対応済み。プロジェクトの容量と健全性の確認から回収までをGUIで完結できるようにする。pruneは取り消せない操作のため本件に含めない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GUIからコミット数・ブランチ数・追跡パス数・つぼみ数・オブジェクト数と、論理容量・実容量・重複排除による節約量を確認できる
- [x] #2 gcの実行前に回収対象のオブジェクト数・一時ファイル数・回収容量を確認でき、確定したときだけ実行される。キャンセルすると何も変更しない
- [x] #3 gcの完了後に実際の回収結果が表示され、容量の表示が更新される。ゴミ箱に保持中のデータが回収対象にならないことが画面から分かる
- [x] #4 GUIから整合性検査を実行でき、問題がなければ検査したオブジェクト数を、問題があれば種類と詳細を表示する
- [x] #5 `doctor`が問題を検出して終了コード1を返した場合に、CLIの実行失敗とは区別して検査結果として表示する
- [x] #6 失敗時は理由を通知し、操作中は他の操作ボタンが無効になる
- [x] #7 自動テストで確認とキャンセル、結果表示、失敗時の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add doctor --report so found issues return normally. 2. Add a maintenance panel from the top bar: stats, gc dry run, confirm, gc, doctor. 3. Explain that trash contents are protected. 4. Tests and docs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added doctor --report so issues return as a result through both serve and one-shot runs, avoiding a Rust change. Verified in the browser harness against the real CLI: stats, clean gc, doctor, gc after a trash purge with confirmation and result.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A maintenance panel now shows repository stats, reclaims space after a confirmed dry run, and runs integrity checks with issues shown as results. Verified with 6 GUI tests, tests/test_doctor_report.py, the full pytest suite, 151 GUI tests and a real-CLI scripted browser run.
<!-- SECTION:FINAL_SUMMARY:END -->
