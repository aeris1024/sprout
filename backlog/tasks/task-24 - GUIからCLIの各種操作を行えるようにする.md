---
id: TASK-24
title: GUIからCLIの各種操作を行えるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:28'
updated_date: '2026-08-09 06:02'
labels: []
dependencies:
  - TASK-23
modified_files:
  - README.md
  - gui/README.md
  - gui/src/App.tsx
  - gui/src/App.css
  - gui/src/App.test.tsx
  - gui/src/lib/sprout.ts
  - gui/src/lib/sprout.test.ts
priority: medium
type: feature
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

Tauri GUI基盤(TASK-23)の上に、Sproutの日常操作を一通りGUIで行える画面を作る。

## 実装方針

以下の画面・機能を実装する。すべて基盤タスクで作ったCLI呼び出し機構を経由する。

1. **ステータス画面**: `status --json`の結果(added/modified/deleted)と追跡・未追跡ファイル一覧を表示。手動リフレッシュに加え、ウィンドウフォーカス時の自動更新程度は入れる。
2. **track/untrack**: ファイル・フォルダ選択ダイアログとドラッグ&ドロップで`track`、一覧からの右クリック等で`untrack`。0件警告(TASK-4)をそのまま表示する。
3. **コミット**: メッセージ入力欄+コミットボタン。サムネイル添付(TASK-21実装済みの場合)のファイル選択も付ける。成功時は新コミットIDを表示する。
4. **履歴**: `log --json`の一覧表示。コミット選択で`show --json`の詳細(ファイル一覧)を表示する。
5. **ブランチ**: 一覧(現在ブランチの強調、コメント表示)、作成、切り替え。切り替え・復元時に未保存変更エラーが返ったら、「変更を破棄して続行(--discard)」を明示的な確認ダイアログ付きで提示する。破棄は取り消せない旨を明記する。
6. **復元**: 履歴からコミットを選んで`restore`。同じく--discard確認フローを通す。

## 注意

- 長時間かかる操作(大きいファイルのcommit/restore)中はUIをブロックし、多重実行を防ぐ(Sprout側もロックで拒否するが、GUIとして自然な待ち表示にする)。
- 破壊的操作(--discard付きのswitch/restore)は必ず確認ダイアログを挟む。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ステータス・追跡状況がGUIで確認できる
- [x] #2 ファイル選択またはドラッグ&ドロップでtrack/untrackができる
- [x] #3 メッセージを入力してコミットできる(サムネイル添付対応)
- [x] #4 履歴とコミット詳細が閲覧できる
- [x] #5 ブランチの一覧・作成・切り替えができる
- [x] #6 restore/switchで未保存変更がある場合、確認ダイアログを経て--discardを選べる
- [x] #7 操作中の多重実行が防止される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. CLIのstatus/log/show/branch/track/untrack/commit/switch/restore JSON契約を型付きヘルパーへ整理する。 2. ステータス画面をタブ型ワークスペースへ拡張し、選択ダイアログとTauriドロップイベントによるtrack、一覧からのuntrack、フォーカス時更新を実装する。 3. メッセージと任意サムネイル付きcommit、履歴一覧・詳細、ブランチ一覧・作成・切り替え、restoreを実装する。 4. uncommitted_changes時だけ取り消し不能を明示した確認ダイアログから--discardを再実行し、全操作中の多重実行を抑止する。 5. Reactユニット/操作テスト、Rust/Python回帰テスト、ビルドと画面確認を行い、READMEを更新する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Tauri IPCの既存run_sproutを型付きで利用し、ステータス、選択・ドロップtrack、一覧untrack、サムネイル付きcommit、履歴・詳細、ブランチ作成・切り替え、restoreをタブ画面へ統合した。uncommitted_changesかつcan_discard=trueの場合だけ取り消し不能の確認後に--discardを再実行する。useRefの即時ロックと全操作ボタンのdisabledで多重実行を防止し、focus時更新を追加した。検証: React 14 tests passed、TypeScript/Vite build成功、Rust 3 tests passed、Python 133 passed・2 skipped、Tauri release build成功、Playwrightで初期・status・commit・branch画面とconsole error 0件を確認。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GUIから日常的なSprout操作を一通り実行できるタブ型ワークスペースを実装した。追跡、サムネイル付きコミット、履歴詳細、ブランチ、確認付き復元・切り替え、多重実行防止を自動テスト14件、全CLI/Rust回帰テスト、Tauri release build、Playwright実画面確認で検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
