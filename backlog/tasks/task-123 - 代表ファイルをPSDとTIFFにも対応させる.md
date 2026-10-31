---
id: TASK-123
title: サムネイル自動生成元をPSDとTIFFにも対応させる
status: To Do
assignee: []
created_date: '2026-10-31 05:45'
updated_date: '2026-10-31 07:51'
labels:
  - thumbnail
dependencies: []
references:
  - src/sprout/repository.py
  - README.md
  - gui/README.md
priority: low
type: enhancement
ordinal: 122000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
サムネイル自動生成元の対応形式はPNG、JPEG、静止WebP、BMPのみで、PSDやTIFFを指定すると「今はサムネイルを作れません」と警告される。制作データでは原本がPSDであることが多く、書き出した画像を別に管理しなくてもサムネイル自動生成元にできると便利である。Pillowで実用的に読めるかは未確認のため、対応範囲の見極めも含む。
用語はTASK-125.12で確定した「サムネイル自動生成元」にそろえる。このタスクの既存の機能範囲は維持する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 実際の制作データに近いPSDとTIFFで読み取りを検証し、対応する範囲を決めて文書化する
- [ ] #2 レイヤーやページが複数あるファイルでも、結合画像または先頭ページから意図どおりのサムネイルが作られる
- [ ] #3 対応しない種類のファイルは保存を失敗させず、理由を報告する
- [ ] #4 大きなファイルでも既存の容量と画素数の上限を守り、保存が過度に遅くならない
- [ ] #5 自動テストで対応する形式と対応しない形式を検証し、README.mdとgui/README.mdを更新する
<!-- AC:END -->
