---
id: TASK-75
title: 選んだ葉（コミット）を1枚だけ削除できるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-29T15:47:00Z'
updated_date: '2026-10-29T16:05:00Z'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - gui/src/App.tsx
priority: medium
type: feature
ordinal: 74000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
prune はタグ間・全履歴の一括間引きのみで、選んだ葉を1枚だけ削除する手段がCLIにもGUIにもない。失敗した保存の取り消しや不要な葉の削除のため、sprout delete-commit とGUIの「この葉を削除」を追加する。ブランチ先端・いまここは親へ移してから削除し（作業ファイルは変更しない）、タグ付きの葉は拒否し、つぼみの起点は親へ付け替える。子は親へつなぎ直す。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 途中の葉を削除すると子が親へつなぎ直され、その葉のファイル・添付・メモ・ラベルが消え、他の葉の内容は変わらない
- [x] #2 ブランチ先端やいまここの葉を削除すると、同じ先端を指すすべてのブランチといまここが親へ移り、作業ファイルは変わらず未保存の変更として残る
- [x] #3 ルートの葉を削除すると子がルートになり、親がない場合はブランチ・いまここがコミットなしになる
- [x] #4 タグ付きの葉は削除を拒否し、何も変更しない
- [x] #5 つぼみの起点になっている葉を削除すると、つぼみの内容を変えず起点が親へ付け替わる
- [x] #6 --dry-runは何も変更せず本番と同じ影響と回収可能容量を報告し、--yesなしの実行は拒否する。JSON出力に対応する
- [x] #7 失敗時はリポジトリを変更しない。削除後もdoctorが正常でgcで容量を回収できる
- [x] #8 GUIの葉の詳細から、影響を確認するダイアログを経て削除でき、キャンセル時は何もしない
- [x] #9 自動テストとREADME・gui/README.mdが更新される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. repository.py: delete_commit(dry_run)を追加。prune の回収可能容量計算を _reclaimable_objects に切り出して共用
2. cli.py: sprout delete-commit COMMIT --dry-run|--yes [--json]
3. GUI: CommitPanelに「この葉を削除」、Appでdry-run→確認→--yes
4. tests/test_delete_commit.py、CLI・GUIテスト
5. README・gui/README更新
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
tests/test_delete_commit.py: 途中の葉・先端といまここ（同じ先端の別名ブランチと削除済みブランチを含む）・ルートと単独ルート・タグ拒否（dry-runも）・つぼみの付け替えとrestore_bud・dry-runと本番の結果一致・トリガーでのDB失敗時の無変更・doctor/gc・CLIの--yes必須とJSONを検証。削除済みブランチ行はCHECK制約でcommit_idがNULLのため、先端の移動対象にはならない。

GUI: CommitPanelに「この葉を削除」（button danger、タグ付きの葉は無効でtitleに理由）。App.deleteCommitは delete-commit --dry-run → deletionSummaryで影響を文章化して confirmDialog（warning、OK「削除」）→ --yes → fetchWorkspace・closeSelection・通知。dry-runの拒否（tagged_commitなど）は確認を出さず通知する。App.test.tsxに確認→実行、キャンセル、拒否、タグ付きで無効の4ケースを追加。

検証: uv run pytest -q（381 passed, 19 skipped）、gui で pnpm exec tsc --noEmit と pnpm test（63 passed）。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
選んだ葉（コミット）を1件だけ削除する sprout delete-commit COMMIT [--dry-run|--yes] [--json] と、GUIの葉の詳細の「この葉を削除」を追加した。同じ先端を指すブランチといまここ・つぼみの起点・子の参照は親へ移し、作業ファイルは変えず未保存の変更として残す。タグ付きの葉は tagged_commit で拒否し、--yes なしの実行も拒否する。DB失敗時は何も変えない。prune の回収可能容量の計算は _reclaimable_objects に切り出して共用した。README（新しい節・コマンド一覧・JSONスキーマ）と gui/README.md を更新。pytest 381 passed / GUI 63 passed。GC はGUIから実行できないため、容量の回収は CLI の sprout gc が必要。
<!-- SECTION:FINAL_SUMMARY:END -->
