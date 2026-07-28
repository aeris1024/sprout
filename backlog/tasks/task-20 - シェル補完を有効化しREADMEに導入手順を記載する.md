---
id: TASK-20
title: シェル補完を有効化しREADMEに導入手順を記載する
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:20'
updated_date: '2026-07-28 18:57'
labels: []
dependencies: []
references:
  - src/sprout/cli.py
priority: low
type: enhancement
ordinal: 20500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

typer(click)にはシェル補完機能が組み込まれているが、現状の`app`は`add_completion`の既定値のままで、READMEにも導入手順がない。コマンド名やオプションの補完が効くと日常操作が楽になる。

## 実装方針

1. `typer.Typer(add_completion=True)`(既定で有効のはずだが明示)を確認し、`sprout --install-completion`と`sprout --show-completion`が動作することを確認する。`main()`が`standalone_mode=False`で呼んでいるため、補完関連のオプション処理が正しく通るかを特に確認する(問題があればcompletion系のみstandaloneで処理する等の対処を検討)。
2. 動作確認はPowerShell(Windows)とbash/zshで行う。
3. READMEに各シェルでの導入手順(`sprout --install-completion powershell`等)を追記する。

さらに進めるなら、ブランチ名やコミットIDの動的補完(typerの`autocompletion`引数でリポジトリから候補を返す)を`switch`/`restore`/`show`に追加する。リポジトリ外で補完が呼ばれた場合に例外を漏らさないよう、`SproutError`を握りつぶして空リストを返すこと。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `sprout --install-completion`と`--show-completion`が動作する
- [x] #2 READMEにシェル補完の導入手順が記載されている
- [x] #3 (任意)switch/restoreでブランチ名の動的補完が効く
- [x] #4 リポジトリ外で補完してもエラーにならない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Typerのadd_completion=Trueを明示し、現行Typerの自動シェル検出に合わせて補完オプションを検証する。 2. switchはブランチ名、show/restore/tagのコミット引数はブランチ名とタグ名を動的候補にし、リポジトリ外では空候補を返す。 3. PowerShell/bash/zshの補完スクリプト生成と、隔離したinstallコールバックをテストする。 4. READMEへ各シェルでの導入・表示手順を記載し、全体テスト後に完了・コミットする。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Typer(add_completion=True)を明示し、現行Typerの自動シェル検出方式でREADMEを更新。PowerShell/bash/zshのスクリプト生成、隔離install、main()経由をテストした。switchはブランチ、show/restore/tagはブランチ+タグを動的補完し、リポジトリ外では空候補を返す。全テスト: 86 passed, 2 skipped。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
PowerShell・bash・zsh向けのTyperシェル補完を明示的に有効化し、導入手順をREADMEへ追加した。ブランチ・タグの動的補完とリポジトリ外での安全な空候補を実装し、全テスト86件成功・2件スキップで検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
