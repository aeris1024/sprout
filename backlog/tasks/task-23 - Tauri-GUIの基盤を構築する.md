---
id: TASK-23
title: Tauri GUIの基盤を構築する
status: To Do
assignee: []
created_date: '2026-07-15 16:27'
labels: []
dependencies:
  - TASK-19
priority: medium
type: feature
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

CLIの各種操作をGUIから行えるデスクトップアプリをTauriで作る。まずアプリの骨格と、SproutのCLIをバックエンドとして呼び出す土台を整える。

## 実装方針

### プロジェクト構成

リポジトリ内に`gui/`ディレクトリを作り、Tauri 2.x + フロントエンド(Vite + React/Svelte等、実装時に選定)で雛形を作成する。Python本体とは独立にビルドできる構成とする。

### CLI連携(本タスクの中核)

GUIはSproutのデータへ直接触らず、必ずCLI経由で操作する(ロック・リカバリ・安全判定の実装を二重化しないため)。

1. TauriのshellプラグインまたはRust側の`Command`で`sprout <cmd> --json`をサブプロセス実行し、stdoutのJSONをパースしてフロントへ返す共通関数(Rustコマンド)を1つ作る。
2. sproutバイナリの解決方法を決める: 初期実装は「PATH上のsproutを使う(uv tool install済み前提)」でよい。将来PyInstaller等でsidecarとして同梱する場合の差し替えポイントをコメントで残す。
3. エラーハンドリング: 終了コード非0のときstderrの`Error: ...`をフロントへ伝搬し、トースト等で表示する。「another Sprout operation is already running」は操作の再試行を促す扱いにする。
4. 作業対象フォルダの選択(ダイアログ)、`.sprout`の有無判定(なければ`sprout init`を提案)、最近開いたプロジェクトの記憶(Tauriのapp data領域に保存)。

### 動作確認のゴール

フォルダを開いて`sprout status --json`の結果が画面に表示されるところまでを本タスクの完了条件とする。個別の操作画面は後続タスク。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `gui/`配下でTauriアプリがビルド・起動できる
- [ ] #2 フォルダ選択でSproutプロジェクトを開ける(未初期化時はinitを提案)
- [ ] #3 CLIを`--json`付きで呼び出す共通機構があり、statusの結果が画面に表示される
- [ ] #4 CLIのエラーがGUI上で通知として表示される
- [ ] #5 最近開いたプロジェクトが記憶される
- [ ] #6 ビルドと開発起動の手順がドキュメント化されている
<!-- AC:END -->
