---
id: TASK-83
title: ファイルに不変IDを導入し改名・移動をまたぐ履歴を追跡する
status: To Do
assignee: []
created_date: '2026-10-29T20:08:00Z'
labels: []
dependencies:
  - TASK-80
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - tests/test_repository.py
  - tests/test_restore_safety.py
  - tests/test_v1_storage.py
  - README.md
priority: high
type: feature
ordinal: 82000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在は通常ファイルをコミットとパスで識別しており、素材の改名・移動後に同じ素材の履歴を追うための不変の識別子がない。未運用の段階でファイルの同一性の規則を決め、将来の素材別履歴やpreviewとの関連付けに利用できるようにする。内容のハッシュは重複排除の識別子として維持し、素材の同一性とは分離する。外部アプリの改名を内容一致だけで自動確定する仕組み、複数親のマージ機能、previewとの関連付けそのものは本件に含めない。保存形式の変更はTASK-80に従う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 追跡ファイルにパスや内容から独立した不変のfile_idがあり、コミットやつぼみの各保存時点におけるパス・内容との関係を保持できる
- [ ] #2 明示的な改名・移動ではIDを維持し、コピーや新規ファイルには別IDを割り当てる。同じ内容の別ファイルをハッシュだけで同一素材にしない。追跡解除・再登録・削除後の同名作成・外部での改名の扱いを文書化する
- [ ] #3 ブランチの分岐・切り替え・過去版の全体/部分復元・つぼみ復元でも保存された素材の同一性を保持し、パスやIDが衝突する場合は既存データを無断で統合・上書きしない
- [ ] #4 CLI・JSONから改名・移動をまたぐ同一素材の履歴と各時点のパスを確認できる。既存のパス指定履歴との使い分けが明確で、GUIが同一性を識別できる
- [ ] #5 ファイルIDを導入しても内容の重複排除を維持し、show・export・archiveなどの読み取り、prune・gc・doctorなどの保護と整合性検査が成立する。削除/取り消し機能とのID復旧規則も定義する
- [ ] #6 改名・移動・コピー・同内容の別素材・同名再作成・枝の分岐・部分復元・つぼみ・衝突と失敗を自動テストで検証し、形式番号と互換性の方針およびREADMEを更新する
<!-- AC:END -->
