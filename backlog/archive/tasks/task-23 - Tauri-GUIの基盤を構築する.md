---
id: TASK-23
title: Tauri GUIの基盤を構築する
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:27'
updated_date: '2026-08-08 20:57'
labels: []
dependencies:
  - TASK-19
  - TASK-44
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
- [x] #1 `gui/`配下でTauriアプリがビルド・起動できる
- [x] #2 フォルダ選択でSproutプロジェクトを開ける(未初期化時はinitを提案)
- [x] #3 CLIを`--json`付きで呼び出す共通機構があり、statusの結果が画面に表示される
- [x] #4 CLIのエラーがGUI上で通知として表示される
- [x] #5 最近開いたプロジェクトが記憶される
- [x] #6 ビルドと開発起動の手順がドキュメント化されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 公式create-tauri-appを使い、gui/へTauri 2 + React TypeScript + Vite + pnpmの独立プロジェクトを作成し、DialogとStoreを組み込む。 2. Rust側にPATHまたは手動指定のsproutを引数配列で起動する単一IPCコマンドを実装し、成功JSONとTASK-44の構造化エラーを型付きでフロントへ返す。 3. 日本語UIでフォルダ選択、未初期化時のinit提案、status表示、通知・ロック再試行、最近使ったプロジェクトとCLIパス保存を実装する。 4. フロントエンドテストとRustテストを追加し、Webビルド・Cargo検査・Tauriビルドを行い、READMEへ開発・ビルド手順を記載する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Tauri 2 + React TypeScript + Vite基盤をgui/へ作成。Rust側run_sproutはPATH/手動CLIを引数配列で起動し、--json自動付与、UTF-8固定、構造化エラー伝搬、Windowsコンソール非表示に対応した。Dialog/Store、日本語のフォルダ選択・init提案・status画面・通知/再試行・最近使ったプロジェクト・CLI設定を実装。Vitest 4件、Cargo test 3件、Tauri release exeビルドと短時間起動、Playwright初期画面を確認済み。

最終検証: React操作テスト6件（フォルダ選択、未初期化提案、init、status、最近使った項目保存、ロック再試行を含む）、Rustテスト3件、Pythonテスト133 passed/2 skipped、pnpm build、cargo fmt --check、Tauri完全ビルドに成功。release exeを短時間起動し、MSIとNSISを生成。Playwrightで日本語初期画面と主要導線を視覚確認した。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Windows向けTauri 2 + React TypeScript GUI基盤を追加した。Rust IPCからSprout CLIのJSON契約を安全に呼び出し、フォルダ選択、未初期化時のinit提案、status表示、構造化エラー通知と再試行、最近使ったプロジェクト、CLIパス設定を実装した。React/Rust/Pythonテスト、Web/Tauriビルド、実行ファイル起動、Playwright表示確認で検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
