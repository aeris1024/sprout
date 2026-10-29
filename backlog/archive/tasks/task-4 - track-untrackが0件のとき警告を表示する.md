---
id: TASK-4
title: track/untrackが0件のとき警告を表示する
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:14'
updated_date: '2026-07-28 18:11'
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
- [x] #1 `untrack`が1件もマッチしなかった場合、警告メッセージが表示される
- [x] #2 `track`が1件もファイルを登録しなかった場合、警告メッセージが表示される
- [x] #3 正常に登録・解除できた場合の出力は従来と変わらない
- [x] #4 CLIテストで0件時の警告表示が検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. track/untrackの戻り値が空の場合だけ標準エラーへ警告し、終了コード0を維持する。 2. 0件時と正常時のCLIテストを追加する。 3. 関連テストと全体テストを実行し、受け入れ条件を確認する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
0件時は標準エラーへ警告し、終了コード0を維持する実装とCLIテストを追加。成功時の従来出力も明示的に検証した。全テスト: 72 passed, 2 skipped。ruffは開発環境に未導入のため未実行。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
track/untrackが0件だった場合に標準エラーへ警告を表示し、互換性のため終了コード0を維持した。0件時と成功時のCLIテストを追加し、全テスト72件成功・2件スキップで回帰がないことを確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
