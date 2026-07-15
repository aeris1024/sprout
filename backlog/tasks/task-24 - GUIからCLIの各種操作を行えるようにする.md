---
id: TASK-24
title: GUIからCLIの各種操作を行えるようにする
status: To Do
assignee: []
created_date: '2026-07-15 16:28'
labels: []
dependencies:
  - TASK-23
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
- [ ] #1 ステータス・追跡状況がGUIで確認できる
- [ ] #2 ファイル選択またはドラッグ&ドロップでtrack/untrackができる
- [ ] #3 メッセージを入力してコミットできる(サムネイル添付対応)
- [ ] #4 履歴とコミット詳細が閲覧できる
- [ ] #5 ブランチの一覧・作成・切り替えができる
- [ ] #6 restore/switchで未保存変更がある場合、確認ダイアログを経て--discardを選べる
- [ ] #7 操作中の多重実行が防止される
<!-- AC:END -->
