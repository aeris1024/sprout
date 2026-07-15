---
id: TASK-20
title: シェル補完を有効化しREADMEに導入手順を記載する
status: To Do
assignee: []
created_date: '2026-07-15 16:20'
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
- [ ] #1 `sprout --install-completion`と`--show-completion`が動作する
- [ ] #2 READMEにシェル補完の導入手順が記載されている
- [ ] #3 (任意)switch/restoreでブランチ名の動的補完が効く
- [ ] #4 リポジトリ外で補完してもエラーにならない
<!-- AC:END -->
