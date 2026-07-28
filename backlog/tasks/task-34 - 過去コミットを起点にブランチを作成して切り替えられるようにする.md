---
id: TASK-34
title: 過去コミットを起点にブランチを作成して切り替えられるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-07-28 20:26'
updated_date: '2026-07-28 20:38'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - README.md
modified_files:
  - README.md
  - src/sprout/cli.py
  - src/sprout/repository.py
  - tests/test_cli.py
  - tests/test_repository.py
priority: medium
type: feature
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
過去のスナップショットから安全に履歴を分岐できるようにする。branch作成時に任意のSTART_POINTを指定でき、必要に応じて作成したブランチへ即座に切り替えられるようにする。restoreで現在ブランチ先端と異なる保存済みスナップショットを表示中にSTART_POINTを省略した場合は、最新コミットから暗黙に分岐せず、分岐元の指定方法を案内する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 branch NAME START_POINTでコミットID、ブランチ名、タグ名を起点に新しいブランチを作成できる
- [x] #2 --switchを指定すると作成したブランチへ切り替わり、作業ツリーがSTART_POINTの内容になる
- [x] #3 START_POINT省略時は従来どおり現在ブランチ先端から作成できる
- [x] #4 現在ブランチ先端と異なる保存済みスナップショットを表示中にSTART_POINTを省略すると、誤分岐せず明確なエラーと指定例を表示する
- [x] #5 作成と切り替えに失敗した場合、半端なブランチを残さない
- [x] #6 READMEとCLIヘルプが更新され、分岐元、切り替え、誤操作防止が自動テストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Repositoryのブランチ作成APIへ任意のSTART_POINTを追加し、指定時はresolve_commitで起点を確定する。 2. --switch付き作成を単一ロック内で処理し、作業ツリー切り替え失敗時は作成ブランチを削除して原子的に扱う。 3. START_POINT省略時、作業ツリーが現在先端とは異なる保存済みスナップショットなら明確なエラーで起点指定を促す。 4. branch CLIへSTART_POINTと--switchを追加し、README・ヘルプ・リポジトリ/CLIテストを更新する。 5. 関連テストと全テストを実行し、差分を独立レビューする。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Cursor CLI（cursor-grok-4.5-high）で実装。branch NAME START_POINT、--switch、復元済みスナップショットでの省略防止、切り替え失敗時のブランチ削除を追加した。検証: 全テスト 102 passed, 2 skipped。sprout branch --help と git diff --check も成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
過去のコミット・ブランチ・タグを起点にブランチを作成し、--switchで即時切り替えできるようにした。restore後の誤分岐と半端なブランチ生成を防止し、README・CLIヘルプ・自動テストを更新。全テスト 102 passed, 2 skippedで確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
