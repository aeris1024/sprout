---
id: TASK-57
title: 新GUIの1画面構成と夜の温室テーマの基盤を作る
status: Done
assignee:
  - '@claude'
created_date: '2026-10-27 15:03'
updated_date: '2026-10-27 19:17'
labels:
  - gui
  - gui-redesign
dependencies:
  - TASK-26
references:
  - gui/design/sprout-map-mockup.html
  - gui/src/App.tsx
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: medium
type: feature
ordinal: 57000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

GUI刷新（doc-1、TASK-51で承認済み）では、5タブと左サイドバーの構成を廃止し、上部バー・芽のマップ・詳細パネルの1画面にする。見た目はC案「夜の温室」で、ライト/ダーク両対応とし、後から配色を差し替えられるようにする。応答速度のため、CLI呼び出しはTASK-26のserve常駐モードを使う。

## ゴール

新しい画面の骨格とテーマ基盤を作り、プロジェクトを開く・初期化する・最近使ったプロジェクト・CLI設定の既存機能を新しい配置へ移す。芽のマップ本体（後続タスク）を差し込める領域を用意する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 画面が上部バー、中央のマップ領域、右側の詳細パネルの1画面で構成され、5タブと左サイドバーが廃止されている
- [x] #2 色・角丸・余白・フォントがテーマ用CSS変数に集約され、C案のライトとダークがOS設定に追従して切り替わり、コンポーネントに色が直書きされていない
- [x] #3 上部バーにプロジェクト名、現在ブランチ、保存状態、ファイル、保存、設定が表示される
- [x] #4 プロジェクト名から最近使ったプロジェクトを選んで開け、一覧から削除でき、未選択時の初期画面にも一覧が表示される
- [x] #5 未初期化フォルダを開いたときに初期化画面が表示され、初期化できる
- [x] #6 CLI設定が歯車から開け、保存できる
- [x] #7 GUIのCLI呼び出しがserve常駐モード経由になり、serveを起動できない場合はエラーを表示するか従来の都度起動へ戻る
- [x] #8 狭いウィンドウでは詳細パネルがマップの下へ移る
- [x] #9 移した既存機能のGUIテストが新しい構成に合わせて更新されている
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 実装と検証（2026-10-28）
- App.tsxを上部バー・中央のスナップショット表示・右側パネルの1画面に再構成し、5タブと左サイドバーを廃止。ProjectMenu（最近使ったプロジェクトの切り替え・削除・フォルダを開く）、FilePanel（追跡管理、旧ステータスタブから移動）、SavePanel（未保存の変更と保存フォーム、旧コミットタブから移動）を追加。中央は当面既存のCommitTreeを表示し、TASK-58で芽のマップに置き換える。
- App.cssをC案「夜の温室」のCSS変数に集約（ライト/ダークをprefers-color-schemeで切り替え）。コンポーネントに色の直書きなし。760px以下で右パネルを下へ移動。
- 起動時の取得をstatusとtreeの2回に削減（log・branchの呼び出しを廃止）。
- Rust側にServeClientを追加し、run_sproutとサムネイル取得を常駐sprout serve経由に変更。serve非対応のCLIや起動直後の終了は都度起動へ戻り、通信が切れた場合はその操作を都度起動で実行して次回再起動する。CLIパス変更時は常駐プロセスを作り直す。
- 旧ブランチタブのブランチ作成フォームは廃止。ブランチ作成はTASK-59の「ここから枝を伸ばす」と、途中からの保存による自動作成で扱う（それまでの間GUIからの名前付き作成はできない）。
- 検証: pnpm test 27 passed（新構成のテストへ更新・追加）、tsc --noEmit成功、cargo test 5 passed、cargo build警告なし。Viteのブラウザ表示でライト/ダークのテーマ変数適用を確認。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GUIを上部バー・スナップショット表示・右パネルの1画面に再構成し、配色C「夜の温室」のCSS変数でライト/ダークに対応した。最近使ったプロジェクト・初期化・CLI設定・追跡管理・保存フォームを新しい配置へ移し、CLI呼び出しを常駐sprout serve経由（非対応時は都度起動）にした。GUIテスト27件・cargo test・型検査成功で確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
