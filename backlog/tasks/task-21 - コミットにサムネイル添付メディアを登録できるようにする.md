---
id: TASK-21
title: コミットにサイズ制限付き画像サムネイルを登録できるようにする
status: To Do
assignee: []
created_date: '2026-07-15 16:26'
updated_date: '2026-07-29 19:46'
labels: []
dependencies:
  - TASK-37
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: medium
type: feature
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

GUIのコミットツリーで各コミットを素早く識別できる、小さな画像サムネイルを登録したい。一覧の表示速度、安全性、実装範囲を明確にするため、thumbnail roleはサイズ制限付きの静止画像だけを対象とする。音声、動画、3Dモデル等はthumbnailへ登録せず、TASK-38のpreview roleと後続GUIレンダラーで扱う。

## 前提となる保存形式

TASK-37のSchema Version 3で用意されるcommit_attachmentsを使用し、role=thumbnailとして保存する。元ファイル名はGUI表示、拡張子の維持、静的アーカイブで利用する。登録後の置き換えではcreated_atを維持してupdated_atを更新する。

## 機能範囲

- commit時に静止画像をサムネイルとして登録できる
- 既存コミットのサムネイルを後付け、置き換え、削除できる
- 対応する静止画像形式を内容とmedia_typeから検証し、音声、動画、アニメーション画像、3Dモデル、文書、未知のバイナリは拒否する
- ツリービューで大量に扱えるよう、サムネイル専用の明確なファイルサイズ上限を設ける
- 添付の実体は既存のobjectsストアへ保存し、通常ファイルと重複排除を共有する
- 添付元はプロジェクト外のファイルも許可する
- GUI、外部ツール、静的アーカイブが画像を取り出せる読み取り手段を提供する

TASK-10のgcとdoctorはcommit_attachmentsが参照するオブジェクトを通常ファイルと同様に扱う。汎用的なクリック表示用ファイルはTASK-38で追加する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 commit時に対応する静止画像をrole=thumbnailとして登録できる
- [ ] #2 既存コミットへのサムネイルの登録、置き換え、削除ができ、置き換え時は作成日時を維持して更新日時が更新される
- [ ] #3 元ファイル名、正しい画像media_type、サイズ、作成日時、更新日時が保持される
- [ ] #4 音声、動画、アニメーション画像、3Dモデル、文書、未知のバイナリをthumbnailとして登録できない
- [ ] #5 定義されたサムネイルサイズ上限を超える画像を明確なエラーで拒否する
- [ ] #6 添付の実体が既存のobjectsストアに保存され、通常ファイルと重複排除される
- [ ] #7 サムネイルを作業ツリーへ影響させずに任意の出力先へ取り出せる
- [ ] #8 showおよびJSON出力でサムネイルの有無、元ファイル名、media_type、サイズ、日時を確認できる
- [ ] #9 gcが参照中のサムネイルを削除せず、doctorがサムネイルオブジェクトの欠落と破損を検査する
- [ ] #10 READMEが更新され、画像形式検証、サイズ上限、登録、置き換え、削除、export、gc、doctorが自動テストで検証される
<!-- AC:END -->
