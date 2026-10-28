---
id: TASK-38
title: コミットに複数の汎用previewを登録し、表示順を変更できるようにする
status: To Do
assignee: []
created_date: '2026-07-29 19:45'
updated_date: '2026-10-28 16:20'
labels: []
dependencies:
  - TASK-21
  - TASK-22
  - TASK-62
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

芽のマップへ常時表示するサムネイルは、小さな静止画像に限定して高速かつ安全に扱う。一方、コミットを選択したときに再生・表示する音声、動画、アニメーション画像、3Dモデル、文書などは、用途とサイズ特性が異なるためサムネイルと分離して登録したい。1コミットに複数のpreviewを付け、目的のファイルを個別に扱い、表示順も変更できるようにする。

## ゴール

TASK-62の新しいSchema Version 1の保存基盤を使い、commit_attachmentsへrole=previewとして任意形式のファイルを複数登録できるようにする。各previewは不変の添付IDで識別し、対象IDを指定して置き換え、削除、取得できる。同名ファイルも別のpreviewとして扱い、置き換えや並べ替えでIDが変わらないこと。

表示順を変更・保存でき、一覧、show、treeおよびJSON出力から保存された順序で各previewの情報を取得できるようにする。ファイルの実体は既存のobjectsストアへ保存し、original_nameとmedia_typeを保持する。

保存層では特定形式へ限定せず、GUIが未対応の形式も失わずに保存・取り出しできることを重視する。表示方法はmedia_typeに応じた後続のGUIレンダラーが担当し、対応するレンダラーがない場合は汎用ファイルとして扱う。

サムネイル向けの小さな固定上限はpreviewへ適用しない。ただし巨大ファイルの誤登録を防ぐため、登録前にサイズと容量影響を明示し、必要に応じて警告や明示的な確認を行えること。

## 対象範囲

previewの追加・IDによる個別操作・表示順変更とCLI・JSON出力を対象とする。thumbnailは従来どおり1コミットに1件とし、代表previewの指定は含めない。今回のBacklog整理ではGUI管理の共通機能を新規タスク化せず、音声・動画・3Dの表示はTASK-39・TASK-40・TASK-41で扱う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 1コミットにrole=previewのファイルを複数追加でき、添付IDで指定したpreviewを個別に置き換え・削除できる
- [ ] #2 画像、音声、動画、3Dモデル、文書、未知のバイナリをファイル形式で拒否せず保存できる
- [ ] #3 各previewの添付ID、元ファイル名、media_type、サイズ、作成日時、更新日時が保持される
- [ ] #4 previewの実体が既存のobjectsストアに保存され、通常ファイルと他の添付との重複排除を共有する
- [ ] #5 GUIが未対応のmedia_typeでも、添付IDで指定したpreviewを内容を失わずに任意の出力先へ取り出せ、作業ツリーへ影響しない
- [ ] #6 サムネイル用の小さな固定上限をpreviewへ適用せず、大容量ファイルは登録前にサイズと容量影響を確認できる
- [ ] #7 一覧、show、treeおよびJSON出力で、添付ID、role、元ファイル名、media_type、サイズ、日時、表示順を保存された順序で確認できる
- [ ] #8 READMEが更新され、複数preview、任意形式、未知形式、大容量警告、IDによる個別操作、並べ替え後の再オープン、同名ファイル、失敗時の非変更が自動テストで検証される
- [ ] #9 previewの表示順を変更・保存でき、再オープン後も一覧、show、treeおよびJSON出力が保存された順序を返す
- [ ] #10 同名ファイルを別のpreviewとして登録でき、置き換えや並べ替えによって添付IDが変わらず、他のpreviewを意図せず変更・削除しない
- [ ] #11 previewの追加・置き換え・削除・取得・並べ替えが失敗した場合、既存previewのデータ・ID・表示順と既存の出力先ファイルを意図せず変更しない
<!-- AC:END -->
