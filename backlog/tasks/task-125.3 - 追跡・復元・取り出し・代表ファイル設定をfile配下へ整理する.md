---
id: TASK-125.3
title: 追跡・復元・取り出し・代表ファイル設定をfile配下へ整理する
status: To Do
assignee: []
created_date: '2026-10-31 07:23'
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
追跡・未追跡の確認 -> file list（区別して確認可能にする）
move -> file move OLD NEW
file-history -> file history FILE_ID
diff -> file diff [LEAF_A] [LEAF_B]
部分restore -> file restore LEAF PATH...（パスは必須）
export -> file export LEAF [PATH...] --output DIR
cat -> file cat LEAF PATH
cover -> file cover show / set IMAGE / clear / apply
file historyは全ブランチの不変素材IDに属する記録であり、leaf list PATHの現在ブランチ・パスの変更履歴とは異なる。file exportのパス省略は葉全体の取り出し。トップレベルstatusの既存機能も保持する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 track/untrack/list/moveで追跡対象の管理と確認ができ、untrackは作業ファイルを削除せずmoveは素材IDを保持する
- [ ] #2 file history FILE_IDで全ブランチ・改名をまたぐ現在と同じ記録を取得でき、file diffの引数なし・1件・2件の比較対象を維持する
- [ ] #3 file restoreは必須のPATHに限る部分復元となり、選択外のファイル・現在位置・ブランチ先端を変更せず、既存のdiscard時のゴミ箱保存を保持する
- [ ] #4 file exportとcatで原本・相対構造・更新日時・バイナリ標準出力の既存動作、出力先の安全検査、force指定を保持する
- [ ] #5 file coverの確認・設定・解除・既存葉への適用が利用でき、applyのdry-run・既存サムネイル保護と既存の生成結果・エラー契約を維持する
- [ ] #6 パス省略・オプションに見えるパス・衝突・上書き拒否・JSONを含め新構文を検証し、V1の保存データを変更する移行を必要としない
<!-- AC:END -->
