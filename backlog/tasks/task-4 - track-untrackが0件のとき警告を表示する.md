---
id: TASK-4
title: track/untrackが0件のとき警告を表示する
status: To Do
assignee: []
created_date: '2026-07-15 16:14'
labels: []
dependencies: []
references:
  - src/sprout/cli.py
priority: medium
type: enhancement
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 問題

パスを打ち間違えて `sprout untrack` を実行しても、何も出力されず終了コード0で終わる。`untrack`は存在しないパスも受け付ける(`_relative_file`を`must_exist=False`で呼ぶ)ため、ユーザーがミスに気づく手段がない。`track`もディレクトリ内にファイルが1つもない場合は同様に無言で成功する。

## 修正方針

`cli.py`の`track`/`untrack`コマンドで、リポジトリ層から返されたリストが空の場合に標準エラーへ警告(例: `Warning: no matching tracked paths` / `Warning: no files were tracked`)を表示する。スクリプト利用を壊さないよう終了コードは0のままにするか、要検討の上で非0にする場合はREADMEに明記する。リポジトリ層のAPI(返り値がリストであること)は変更不要。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `untrack`が1件もマッチしなかった場合、警告メッセージが表示される
- [ ] #2 `track`が1件もファイルを登録しなかった場合、警告メッセージが表示される
- [ ] #3 正常に登録・解除できた場合の出力は従来と変わらない
- [ ] #4 CLIテストで0件時の警告表示が検証されている
<!-- AC:END -->
