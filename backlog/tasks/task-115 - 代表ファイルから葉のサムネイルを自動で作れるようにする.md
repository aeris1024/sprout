---
id: TASK-115
title: 代表ファイルから葉のサムネイルを自動で作れるようにする
status: To Do
assignee: []
created_date: '2026-10-30 18:07'
labels:
  - storage
  - thumbnail
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/preview_image.py
  - src/sprout/cli.py
  - gui/src/components/SavePanel.tsx
  - README.md
priority: medium
type: feature
ordinal: 114000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
今はサムネイルを毎回手動で登録しないと、マップの葉が「画像なし」になる。プロジェクトで`poster.png`のような代表ファイルを指定し、保存時にそこからサムネイルを自動で作れるとマップの価値が大きく上がる。素材IDがあるため、ファイルを移動しても指定を保てる。手動登録の補助を扱うTASK-29とは別の機能である。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CLIとGUIからプロジェクトの代表ファイルを指定・変更・解除でき、指定は素材IDで保持され、改名・移動後も有効である
- [ ] #2 保存時に代表ファイルが対応する画像なら、サイズと形式の制限を満たすサムネイルが自動で登録される。手動で指定した場合はそれを優先する
- [ ] #3 代表ファイルがない、画像でない、変換できない場合でも保存は成功し、サムネイルなしになった理由を確認できる
- [ ] #4 既存のコミットへ適用する操作は明示的に実行したときだけ動き、手動のサムネイルを上書きしない
- [ ] #5 自動テストで生成、優先順位、失敗時の保存、改名後の動作を検証し、README.mdとgui/README.mdを更新する
<!-- AC:END -->
