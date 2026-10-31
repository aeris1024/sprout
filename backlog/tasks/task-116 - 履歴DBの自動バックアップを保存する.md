---
id: TASK-116
title: 履歴DBの自動バックアップを保存する
status: To Do
assignee: []
created_date: '2026-10-30 18:07'
updated_date: '2026-10-31 09:31'
labels:
  - storage
dependencies:
  - TASK-125.5
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - README.md
priority: low
type: feature
ordinal: 115000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
パスと履歴の対応は`repository.db`にしかなく、これが壊れると`objects`だけでは履歴を復元できない。履歴を長期に保つツールとして、DBの一貫したバックアップを自動で保持し、破損時に戻せるようにする。

CLI再編後の診断入口はmaintenance doctor、回収はmaintenance gc。静的なleaf archiveとは用途を区別する。
一貫したDBだけが残っても、そのDBが参照するobjectsを後のgcが回収すれば復旧できない。保持中バックアップからの復旧に必要な実体の保持範囲・世代削除時の解放・回収との整合を、着手時に明示して検証する。具体的な保持方式や新たな保存形式をこのタスク記述だけで決定しない。
DB破損時は通常のリポジトリ読み込みが失敗し得るため、診断がそこで止まってバックアップを案内できない経路も対象にする。自動復旧を実行する機能ではなく、保全と手順による復旧を扱う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 保存などの更新の後、一定の間隔でDBの一貫したバックアップが`.sprout`内に世代管理で作られ、古い世代は自動で削除される
- [ ] #2 バックアップの失敗は通常操作を失敗させず、正規maintenance doctorから確認できる
- [ ] #3 maintenance doctorは通常のDBオープンが破損で失敗する場合も診断し、利用できるバックアップがあれば案内する
- [ ] #4 バックアップから戻す手順があり、戻す前に現在のDBを保全する。バックアップ以降に作られたコミットが失われることを確認できる
- [ ] #5 保持中バックアップが参照する復旧に必要なobjectsをgc後も利用でき、古い世代の削除後は通常の履歴/ゴミ箱等から不要な実体を回収できる。保持・回収方式を明示して検証する
- [ ] #6 自動テストで作成、世代管理、破損からの復旧を検証し、README.mdを更新する
<!-- AC:END -->
