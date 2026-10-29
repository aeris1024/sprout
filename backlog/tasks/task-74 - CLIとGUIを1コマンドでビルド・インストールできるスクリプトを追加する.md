---
id: TASK-74
title: CLIとGUIを1コマンドでビルド・インストールできるスクリプトを追加する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-29T15:39:00Z'
updated_date: '2026-10-29T15:47:00Z'
labels:
  - build
dependencies: []
references:
  - scripts/install.ps1
  - gui/src-tauri/tauri.conf.json
  - README.md
priority: medium
type: feature
ordinal: 73000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景
現在はCLIを`uv tool install .`、GUIを`gui`で`pnpm install`と`pnpm tauri build`を実行して作ったインストーラーで別々に導入する必要があり、手順が多い。GUIはPATH上のCLIを呼ぶため、両方を揃える必要もある。

## ゴール
開発ツール（uv、Node.js、pnpm、Rust）が入ったWindows環境で、リポジトリのルートから1コマンド（またはダブルクリック）でCLIのインストール、GUIのビルド、GUIのインストールまで完了できるようにする。CLIだけ・ビルドだけの実行も選べるようにする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ルートのinstall.cmdまたはscripts/install.ps1の1コマンドで、CLIのインストールとGUIのビルド・インストールが完了する
- [x] #2 必要なツール（uv、node、pnpm、cargo）がない場合は、何が足りないかと導入方法を示して中止する
- [x] #3 -CliOnlyでCLIだけ、-BuildOnlyでインストールせずGUIインストーラーの作成だけを行える
- [x] #4 既存のCLI・GUIがインストール済みでも、再実行で最新のコードに更新できる
- [x] #5 CLIのインストール先がPATHにない場合は警告と対処方法を表示する
- [x] #6 READMEとgui/README.mdに使い方が記載される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. scripts/install.ps1を追加する。必要ツール（uv、node、pnpm、cargo）を確認し、足りなければ導入方法を示して中止する。
2. CLI: `uv tool install --force --reinstall .`で更新込みでインストールし、`uv tool dir --bin`がPATHにない場合は`uv tool update-shell`を案内する。
3. GUI: gui/で`pnpm install --frozen-lockfile`、`pnpm tauri build --bundles nsis`（管理者権限不要のユーザー単位インストーラー）を実行し、作成されたsetup.exeを実行する。
4. -CliOnly（CLIのみ）と-BuildOnly（インストーラー作成のみ）を用意する。
5. 実行ポリシーに左右されないよう、ルートにinstall.cmd（PowerShellを-ExecutionPolicy Bypassで起動）を置く。
6. 検証は一時的なUV_TOOL_DIRでCLI導入を確認し、GUIは-BuildOnlyでインストーラー作成まで確認する。実際のGUIインストールはユーザー確認後に行う。
7. READMEとgui/README.mdを更新する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
検証（2026-10-30、Windows PowerShell 5.1）:
- PATHからツールを外して実行すると、uv・node・pnpm・cargoの不足と導入方法を表示して終了コード1で止まった。
- UV_TOOL_DIR・UV_TOOL_BIN_DIRを一時フォルダへ向けて-CliOnlyを実行し、sprout 0.1.0の導入と、PATHにない場合の警告を確認した（install.cmd経由も同様）。
- 同条件で-BuildOnlyを実行し、135秒でgui/src-tauri/target/release/bundle/nsis/Sprout_0.1.0_x64-setup.exeが作成された。
- スクリプトはWindows PowerShell 5.1で日本語が化けないようUTF-8（BOM付き）・CRLFで保存した。install.cmdは実行ポリシーに関係なく動くよう-ExecutionPolicy Bypassで起動し、ダブルクリック時に結果が見えるよう最後にpauseする。

- フル実行（2026-10-30）: 既存のSprout GUI 0.1.0とuv toolのsproutがある状態で`scripts/install.ps1`を実行し、97秒・終了コード0で完了した。%LOCALAPPDATA%\Sprout\sprout-gui.exeが今回の実行時刻で更新され、~/.local/bin/sprout.exeはTASK-46の`stats --json`に対応した現在のコードになった。
- 出力をファイルへリダイレクトした場合、cargoの標準エラー出力がNativeCommandErrorとして表示されるが、処理は止まらず完了する。コンソールから実行した場合は通常の表示になる。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
ルートのinstall.cmd（ダブルクリック可）とscripts/install.ps1を追加し、1コマンドでCLIのインストール（uv tool install --force --reinstall）、GUIのビルド（pnpm tauri build --bundles nsis）、GUIのユーザー単位サイレントインストールまで行えるようにした。必要なツールがなければ導入方法を示して中止し、CLIの導入先がPATHにない場合は警告する。-CliOnlyと-BuildOnlyを用意した。ツール不足、CLIのみ、ビルドのみ、既存インストールへの上書き（フル実行、97秒）を確認した。READMEとgui/README.mdを更新した。
<!-- SECTION:FINAL_SUMMARY:END -->
