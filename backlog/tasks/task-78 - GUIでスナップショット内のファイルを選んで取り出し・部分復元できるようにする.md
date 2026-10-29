---
id: TASK-78
title: GUIでスナップショット内のファイルを選んで取り出し・部分復元できるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-29T16:34:00Z'
updated_date: '2026-10-29T16:56:00Z'
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
- [x] #1 葉の詳細から保存済みファイルのパス・サイズを確認し、1件以上のファイルやディレクトリ配下を操作対象として選択できる
- [x] #2 選択したファイルだけを指定フォルダへ取り出せる。相対パス構造と保存時の更新日時を保ち、作業ファイル・追跡状態・現在位置・ブランチ先端を変更しない
- [x] #3 選択したファイルだけを作業フォルダへ部分復元でき、選択外の追跡ファイル・現在位置・ブランチ先端を変更せず、完了後に未保存の変更表示を更新する
- [x] #4 部分復元前に対象と影響を確認でき、キャンセル時は変更しない。対象に未保存変更がある場合は自動で破棄せず、破棄を伴う再実行は明示的な確認後にだけ行う
- [x] #5 取り出し先の既存ファイルを無断で上書きしない。未追跡ファイルの衝突・リンク・選択外ファイルへの影響などCLIが拒否するケースは構造化エラーで表示し、CLIの保護を迂回しない
- [x] #6 ファイル選択と部分取り出し・復元、選択外ファイルと参照の維持、キャンセル、未保存変更や衝突時の動作を検証する自動テストと、gui/README.md の操作説明が追加される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 葉の詳細にパス・サイズとファイル／フォルダ選択を追加する。2. 選択パスをCLI export/restoreへ渡し、復元前確認と未保存変更の破棄再確認を実装する。3. 選択・キャンセル・エラー・部分復元後の状態更新をDOMテストで検証し、既存CLI安全性テストとビルドを実行、操作説明を更新する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
検証: CLI全体382 passed / 19 skipped（既存の部分復元・exportの相対パス/mtime・衝突/リンク保護を含む）。GUI既存と追加の統合テスト80件、SnapshotFilesの選択・解除・空状態・別スナップショットでのリセット2件が成功。TypeScript + Vite build成功。DOMテストで選択パスのみのCLI引数、復元後の変更表示更新、キャンセル、未保存変更の破棄許可/拒否、構造化エラーと無断force/discardの禁止を確認。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
葉の詳細に保存済みファイルのパス・サイズ、ファイル/フォルダ配下の選択を追加し、選択したファイルだけを取り出し・部分復元できるようにした。復元前に対象と影響を確認し、未保存変更の破棄はCLIの拒否後に別途確認する。選択外ファイル・現在位置・ブランチ先端を維持する既存CLIの保護を利用。操作説明とGUIテストを追加。
<!-- SECTION:FINAL_SUMMARY:END -->
