---
id: TASK-125.3
title: 追跡・差分・部分復元・取り出しをfile配下へ整理する
status: To Do
assignee: []
created_date: '2026-10-31 07:23'
updated_date: '2026-10-31 07:36'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - tests/test_cli.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 127000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ファイルに関する正規操作をfileへ集約する。
track/untrack -> file track/untrack PATH...
追跡・未追跡の確認 -> file list
move -> file move OLD NEW
diff -> file diff [LEAF_A] [LEAF_B]
部分restore -> file restore LEAF PATH...（パス必須）
export -> file export LEAF [PATH...] --output DIR
cat -> file cat LEAF PATH
file-historyはTASK-125.10でleaf list --file-id FILE_IDへ、coverはTASK-125.12でleaf thumbnailの自動生成元操作へ統合する。file historyとfile coverを正規の別入口として追加しない。
file exportのパス省略は葉全体の取り出し。statusの既存機能を維持し、全体移動と部分復元の役割はTASK-125.9と整合させる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 track/untrack/list/moveで追跡対象の管理と確認ができ、untrackは作業ファイルを削除せずmoveは素材IDを保持する
- [ ] #2 file diffの引数なし・1件・2件の比較対象を維持する。素材ID履歴はleaf listへの統合タスク、自動生成元はleaf thumbnailへの統合タスクへ委ね、file history/file coverを別の正規入口にしない
- [ ] #3 file restoreは必須のPATHに限る部分復元となり、選択外のファイル・現在位置・ブランチ先端を変更せず、既存のdiscard時のゴミ箱保存を保持する
- [ ] #4 file exportとcatで原本・相対構造・更新日時・バイナリ標準出力の既存動作、出力先の安全検査、force指定を保持する
- [ ] #5 パス省略・オプションに見えるパス・衝突・上書き拒否・JSONを含め新構文を検証し、V1の保存データを変更する移行を必要としない
<!-- AC:END -->
