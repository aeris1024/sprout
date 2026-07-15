---
id: TASK-10
title: gcコマンドを追加して参照されないオブジェクトを削除する
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
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

`.sprout/objects`は増える一方で、不要オブジェクトを削除する手段がない(READMEの既知の制限)。また`commit`はオブジェクトを保存してから「file changed while committing」等の検証を行うため、コミットが失敗するとどのコミットからも参照されない孤児オブジェクトが残り、蓄積し続ける。

## 実装方針

`sprout gc`コマンドを追加する。

1. リポジトリロック(`@locked`)の下で実行する。実行中の他操作との競合を防ぐため必須。
2. `SELECT DISTINCT object_hash FROM commit_files`で参照中のハッシュ集合を取得する。
3. `objects/xx/<hash>`を走査し、集合に含まれないファイルを削除する。空になった`xx`ディレクトリも削除する。
4. `tmp/`に残った古い一時ファイル(`object-*`)も削除する。
5. 削除した個数と解放したバイト数を表示する。`--dry-run`オプションで削除対象の一覧表示のみ行えるようにする。

将来「コミット削除」機能が入ると参照集合が変わるだけで同じロジックが使えるため、参照集合の取得は独立した関数にしておくとよい。READMEの「現在の制限」からGC未対応の記述を更新すること。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `sprout gc`がどのコミットからも参照されないオブジェクトを削除する
- [ ] #2 参照中のオブジェクトは削除されない
- [ ] #3 `--dry-run`で削除せずに対象を確認できる
- [ ] #4 実行中は他のSprout操作と排他される
- [ ] #5 削除数と解放サイズが表示される
- [ ] #6 READMEとコマンド一覧が更新されている
- [ ] #7 孤児オブジェクトの削除と参照オブジェクトの保護がテストで検証されている
<!-- AC:END -->
