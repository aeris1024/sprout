---
id: TASK-38
title: コミットにクリック表示用の汎用previewファイルを登録できるようにする
status: To Do
assignee: []
created_date: '2026-07-29 19:45'
updated_date: '2026-07-29 19:46'
labels: []
dependencies:
  - TASK-21
  - TASK-22
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - README.md
priority: low
type: feature
ordinal: 38000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

ツリービューへ常時表示するサムネイルは、小さな静止画像に限定して高速かつ安全に扱う。一方、コミットを選択したときに再生・表示する音声、動画、アニメーション画像、3Dモデル、文書などは、用途とサイズ特性が異なるためサムネイルと分離して登録したい。

## ゴール

Schema Version 3のcommit_attachmentsへrole=previewとして任意形式の単一ファイルを登録、置き換え、削除、取得できるようにする。ファイルの実体は既存のobjectsストアへ保存し、original_nameとmedia_typeを保持する。

保存層では特定形式へ限定せず、GUIが未対応の形式も失わずに保存・取り出しできることを重視する。表示方法はmedia_typeに応じた後続のGUIレンダラーが担当し、対応するレンダラーがない場合は汎用ファイルとして扱う。

サムネイル向けの小さな固定上限はpreviewへ適用しない。ただし巨大ファイルの誤登録を防ぐため、登録前にサイズを明示し、必要に応じて警告や明示的な確認を行えること。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 コミットごとにrole=previewのファイルを登録、置き換え、削除できる
- [ ] #2 画像、音声、動画、3Dモデル、文書、未知のバイナリをファイル形式で拒否せず保存できる
- [ ] #3 元ファイル名、media_type、サイズ、作成日時、更新日時が保持される
- [ ] #4 previewの実体が既存のobjectsストアに保存され、通常ファイルと他の添付との重複排除を共有する
- [ ] #5 GUIが未対応のmedia_typeでも内容を失わず、作業ツリーへ影響させずに任意の出力先へ取り出せる
- [ ] #6 サムネイル用の小さな固定上限をpreviewへ適用せず、大容量ファイルは登録前にサイズと容量影響を確認できる
- [ ] #7 show、treeおよびJSON出力でrole、元ファイル名、media_type、サイズ、日時を確認できる
- [ ] #8 READMEが更新され、任意形式、未知形式、大容量警告、登録、置き換え、削除、exportが自動テストで検証される
<!-- AC:END -->
