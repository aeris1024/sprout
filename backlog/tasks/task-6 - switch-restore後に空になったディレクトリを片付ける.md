---
id: TASK-6
title: switch/restore後に空になったディレクトリを片付ける
status: To Do
assignee: []
created_date: '2026-07-15 16:15'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
priority: low
type: bug
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 問題

`_materialize`は復元対象に含まれないファイルをbackupディレクトリへ退避するが、ファイルが消えて空になったディレクトリは作業フォルダに残り続ける。ブランチ切り替えを繰り返すと空ディレクトリが蓄積する。

## 修正方針

`_materialize`の成功後(`_finalize_materialization`の後)に、退避・削除したパス(`current - set(target)`のファイルがあった親ディレクトリ)から`self.root`方向へ遡り、空のディレクトリを`os.rmdir`で削除する。注意点:

- `.sprout`(CONTROL_DIR)と`self.root`自体は削除しない。
- 未追跡ファイルが残っているディレクトリは空でないため`os.rmdir`が失敗する。これは正常系なので握りつぶす(空のときだけ消える挙動が正しい)。
- ロールバック(`_rollback_materialization`)側は既に`destination.parent.mkdir(parents=True)`で復元先ディレクトリを再作成するため変更不要。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ブランチ切り替えでファイルが無くなったディレクトリが空であれば削除される
- [ ] #2 未追跡ファイルが残るディレクトリは削除されない
- [ ] #3 プロジェクトルートと`.sprout`は削除されない
- [ ] #4 空ディレクトリの削除がテストで検証されている
<!-- AC:END -->
