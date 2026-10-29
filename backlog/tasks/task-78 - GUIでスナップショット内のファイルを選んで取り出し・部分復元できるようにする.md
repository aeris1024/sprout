---
id: TASK-78
title: GUIでスナップショット内のファイルを選んで取り出し・部分復元できるようにする
status: To Do
assignee: []
created_date: '2026-10-29T16:34:00Z'
labels: []
dependencies: []
references:
  - src/sprout/cli.py
  - gui/src/components/CommitPanel.tsx
  - gui/src/App.tsx
  - tests/test_restore_safety.py
  - tests/test_cli.py
priority: high
type: feature
ordinal: 77000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在のGUIの葉の詳細は保存ファイル数を示し、全ファイルを取り出す操作に対応しているが、必要な素材だけを選んで取り出したり過去の版に戻したりできない。CLIの sprout export COMMIT PATH... と sprout restore COMMIT PATH... をGUIから利用し、プロジェクト全体を過去へ移動せずに必要なファイルだけを再利用できるようにする。対象はスナップショットに保存した制作ファイルであり、ファイル差分の比較（TASK-77）、ファイル別履歴、preview添付の管理（TASK-72）は別タスクで扱う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 葉の詳細から保存済みファイルのパス・サイズを確認し、1件以上のファイルやディレクトリ配下を操作対象として選択できる
- [ ] #2 選択したファイルだけを指定フォルダへ取り出せる。相対パス構造と保存時の更新日時を保ち、作業ファイル・追跡状態・現在位置・ブランチ先端を変更しない
- [ ] #3 選択したファイルだけを作業フォルダへ部分復元でき、選択外の追跡ファイル・現在位置・ブランチ先端を変更せず、完了後に未保存の変更表示を更新する
- [ ] #4 部分復元前に対象と影響を確認でき、キャンセル時は変更しない。対象に未保存変更がある場合は自動で破棄せず、破棄を伴う再実行は明示的な確認後にだけ行う
- [ ] #5 取り出し先の既存ファイルを無断で上書きしない。未追跡ファイルの衝突・リンク・選択外ファイルへの影響などCLIが拒否するケースは構造化エラーで表示し、CLIの保護を迂回しない
- [ ] #6 ファイル選択と部分取り出し・復元、選択外ファイルと参照の維持、キャンセル、未保存変更や衝突時の動作を検証する自動テストと、gui/README.md の操作説明が追加される
<!-- AC:END -->
