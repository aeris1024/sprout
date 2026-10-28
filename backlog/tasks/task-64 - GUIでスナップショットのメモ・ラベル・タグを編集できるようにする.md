---
id: TASK-64
title: GUIでスナップショットのメモ・ラベル・タグを編集できるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-28 16:58'
updated_date: '2026-10-28 17:37'
labels: []
dependencies:
  - TASK-63
references:
  - gui/src/components/CommitPanel.tsx
  - gui/src/App.tsx
  - src/sprout/cli.py
  - src/sprout/repository.py
priority: medium
type: feature
ordinal: 64000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
メモ・ラベル・タグはCLIで操作できるが、GUIでは表示も編集もできない。またtagコマンドはJSON出力に対応しておらず、常に--jsonを付けて呼び出すGUIからは使えない。タグのコメントは作成後に変更できない。

スナップショットの詳細から、メモ・ラベル・タグを確認・編集できるようにする。

対象外: タグの名前変更、ラベルによる絞り込み表示。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tagコマンドが作成・削除・一覧・コメント変更でJSONを出力し、既存のテキスト出力と名前による操作を維持する
- [x] #2 CLIで既存タグのコメントを変更でき、存在しないタグは構造化エラーで拒否される
- [x] #3 スナップショットの詳細でメモを表示・編集・削除でき、上限を超えるメモはエラーとして通知され入力内容が失われない
- [x] #4 スナップショットの詳細でラベルを一覧・追加・削除でき、空・長すぎる・上限数を超えるラベルはエラーとして通知される
- [x] #5 スナップショットの詳細でタグをコメント付きで一覧・作成・コメント変更・削除でき、削除前に確認が表示される
- [x] #6 編集後にマップと詳細の表示が更新され、コミットID・親子関係・ファイル・添付・ブランチは変化しない
- [x] #7 CLIとGUIの自動テストで各操作と入力エラーを検証し、READMEとgui/READMEを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Repository: 既存タグのコメントを置き換えるset_tag_commentを追加し、存在しないタグはSproutErrorで拒否する。
2. CLI: tagに--jsonと--set-commentを追加する。作成・コメント変更はタグ情報（name・commit_id・comment・created_at）、削除はnameとdeleted、一覧はタグ情報の配列を返す。既存のテキスト出力と組み合わせ検証を維持する。
3. GUI: 詳細パネルにメモ（表示・編集・空で削除）、ラベル（チップ表示・追加・削除）、タグ（コメント付き一覧・作成・コメント変更・確認付き削除）を追加する。操作はnote・label・tag CLIを呼び、成功後にtreeとshowを取り直す。失敗時は入力内容を保持する。
4. Python・GUIテストで各操作、入力エラー、コミットの不変性を確認し、READMEとgui/READMEを更新する。pytest全体、vitest、tsc、vite buildで検証する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 実装

Repositoryにset_tag_commentを追加した。CLIのtagに--jsonと--set-commentを追加し、作成・コメント変更はタグ情報、削除はnameとdeleted、一覧はタグ情報の配列を返す。既存のテキスト出力は維持し、--set-commentと名前なし・作成引数・--deleteの組み合わせは拒否する。

GUIはCommitAnnotationsコンポーネントを追加し、葉の詳細にメモ・ラベル・タグの欄を設けた。Appのexecuteは成功時にtrueを返すようにし、編集が拒否された場合は入力内容を残す。編集はnote・label・tag CLIを呼び、成功後にstatus・tree・showを取り直す。空のメモはnote --deleteで削除する。タグの削除は確認ダイアログの後に実行する。詳細一覧のタグ行は、コメント付きのタグ欄へ移した。

## 検証

- Python全体: 288 passed、19 skipped（環境条件）。新規のtest_tag_cli_json_and_comment_editingで、JSON出力・コメントの変更と空への変更・未知タグの拒否・不正な組み合わせの拒否・削除と、コミット内容が変わらないことを確認した。メモ・ラベルがコミットを変えないことは既存のTASK-28のテストで担保している。
- GUI: vitest 44 passed。メモの保存・拒否時の入力保持・削除、ラベルの追加・上限超過時の入力保持・削除、タグの作成・コメント変更・確認キャンセルと削除をDOMテストで確認した。
- tsc・vite buildが成功。git diff --checkも成功。
- Tauriの実ウィンドウでの手動確認は未実施。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
CLIのtagをJSON出力とコメント変更に対応させ、GUIの葉の詳細でメモ・ラベル・タグを確認・編集できるようにした。拒否された場合は入力を保持し、タグの削除には確認を表示する。Python 288件成功（19件は環境条件でスキップ）、GUI 44件成功、型チェック・ビルド・差分チェックで確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
