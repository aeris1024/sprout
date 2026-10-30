---
id: TASK-113
title: 破棄した未保存の作業をゴミ箱から戻せるようにする
status: To Do
assignee: []
created_date: '2026-10-30 18:06'
labels:
  - storage
  - v1
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/trash.py
  - src/sprout/cli.py
  - gui/src/components/TrashPanel.tsx
  - README.md
priority: high
type: feature
ordinal: 112000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`bud --drop`と`restore --discard`、`switch --discard`は未保存の作業を消すが、ゴミ箱に何も残さない。これらの内容は他のどこにも残っていないため、誤操作すると取り戻せない。GUIの「つぼみを捨てる」と、未保存変更を破棄して戻す操作も同じである。アプリは未運用のため、V1の保存形式を直接変更してよい。形式番号は1のままとし、旧構造からの移行は用意しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 つぼみを捨てるとゴミ箱へ移り、ファイルの内容と素材ID、名前を含めて復旧できる
- [ ] #2 `restore --discard`と`switch --discard`で失われる追跡ファイルの内容が、実行前に復旧可能な形で保存される
- [ ] #3 破棄する変更がない場合は復旧項目を作らない
- [ ] #4 復旧時に競合がある場合は変更せず理由を表示する。完全削除するまで内容はgcで回収されない
- [ ] #5 GUIのゴミ箱に新しい種類の項目が分かる名前で表示され、破棄の確認文が実際の動作と一致する
- [ ] #6 自動テストで保存、復旧、競合、完全削除、gcとの関係を検証し、README.mdとgui/README.mdを更新する
<!-- AC:END -->
