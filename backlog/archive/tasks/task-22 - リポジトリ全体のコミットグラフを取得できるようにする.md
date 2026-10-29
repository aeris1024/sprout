---
id: TASK-22
title: リポジトリ全体のコミットグラフを取得できるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:27'
updated_date: '2026-08-08 19:09'
labels: []
dependencies:
  - TASK-19
  - TASK-21
  - TASK-28
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: medium
type: feature
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

現在のlogはHEADから親を遡る単線の履歴しか見えない。GUIと静的アーカイブでリポジトリ全体をツリー構造として扱うため、削除済みブランチ由来を含む全コミット、親子関係、現在の参照、添付、メモ、ラベルをまとめて取得できるAPIとコマンドが必要である。

## ゴール

全コミットを平坦な機械可読データとして返し、利用側がparent_idから子リストや表示レーンを構築できるようにする。コミットにはID、親ID、作成時ブランチ名、日時、メッセージ、サムネイル等の添付メタデータ、メモ、ラベルを含める。ブランチ先端とタグは現在の参照として別に返す。

人間向けには全履歴を簡易ツリーとして表示し、ブランチ先端、タグ、サムネイル、メモ、ラベルの存在を識別できるようにする。JSON出力はGUIとTASK-36の静的アーカイブ生成が共通利用できる安定した形式とする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 全ブランチと削除済みブランチ由来を含むDB上の全コミットが親子関係付きで取得される
- [x] #2 treeの人間向け表示で分岐した履歴、ブランチ先端、タグ、サムネイル、メモ、ラベルの存在を確認できる
- [x] #3 treeのJSON出力に全コミットのID、親ID、作成時ブランチ名、日時、メッセージ、添付メタデータ、メモ、ラベルが含まれる
- [x] #4 JSON出力に現在のブランチ先端とタグが含まれ、コミットの作成時ブランチ名と現在の参照を区別できる
- [x] #5 分岐、削除済みブランチ、タグ、添付、メモ、ラベルを含む履歴で出力が自動テストされ、READMEに表示形式とJSONスキーマが記載される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 全コミット、汎用添付、注記、ブランチ先端、タグを表す不変データ型と一貫したRepository読み取りAPIを追加する。 2. 注記一括取得を接続共有できる内部処理へ整理し、全履歴を新しい順で安定して返す。 3. treeコマンドの平坦なJSONスキーマと、親子関係をASCII枝で示す人間向け表示を実装する。 4. 分岐、削除済みブランチ由来、現在参照、タグ、サムネイル、メモ、ラベル、空リポジトリをRepository/CLIテストで検証する。 5. READMEへ表示例とJSONスキーマを追加し、全テストを実行する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
単一の読み取りトランザクションで全コミット、汎用添付、メモ、ラベル、現在のブランチ先端、タグを返すCommitGraph APIを追加した。treeは人間向けASCII枝と平坦なJSONを提供し、JSONコミットは新しい順で安定化した。検証: uv run pytest --basetemp .test-tmp-task22c -p no:cacheprovider -q（123 passed, 2 skipped）、tree限定テストとCLIヘルプ成功、git diff --check成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
削除済みブランチ由来を含む全コミットグラフと現在参照を取得できるRepository APIおよびtreeコマンドを実装した。添付・メモ・ラベルを統合し、READMEの表示例／JSONスキーマと全123テスト成功で検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
