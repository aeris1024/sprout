---
id: TASK-12
title: diffコマンドを追加してコミット間のファイル差分を表示する
status: To Do
assignee: []
created_date: '2026-07-15 16:17'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: medium
type: feature
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

restoreやswitchの前に「何が変わるか」を確認する手段がない。内容差分(バイナリ差分)は不要で、ファイルレベルの added / modified / deleted 一覧があれば十分実用になる。

## 実装方針

`sprout diff [COMMIT_A] [COMMIT_B]`コマンドを追加する。

1. 引数の解決は既存の`resolve_commit`(完全ID、プレフィックス、ブランチ名)を再利用する。
2. 比較ロジック: `manifest(a)`と`manifest(b)`を取得し、パス集合の差と`(object_hash, size)`の不一致で added / modified / deleted を分類する。`status()`と同様のシンプルな辞書比較で実装できる。
3. 引数の省略時挙動:
   - 引数2つ: コミットAからコミットBへの差分。
   - 引数1つ: 指定コミットと作業ツリーの差分(作業ツリー側は追跡ファイルをハッシュしてsignatureを作る)。
   - 引数なし: HEADコミットと作業ツリーの差分(`status`と同等だが同じ出力形式)。
4. 出力形式は`status`に合わせ`added <path>`等の行形式。サイズ変化(`1234 -> 5678`)を添えると親切。

リポジトリ層に`diff_manifests(a, b) -> list[StatusEntry]`のような純粋関数を作り、CLI層で表示する構成にするとテストしやすい。READMEのコマンド一覧に追記する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 2つのコミット指定でファイルレベルの差分(added/modified/deleted)が表示される
- [ ] #2 コミット指定1つで作業ツリーとの差分が表示される
- [ ] #3 ブランチ名・IDプレフィックスでコミットを指定できる
- [ ] #4 READMEのコマンド一覧に`diff`が追記されている
- [ ] #5 差分の分類がテストで検証されている
<!-- AC:END -->
