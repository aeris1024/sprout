---
id: TASK-21
title: コミットにサイズ制限付き画像サムネイルを登録できるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:26'
updated_date: '2026-08-08 17:56'
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
- [x] #1 commit --thumbnailでPNG・JPEG・WebPの静止画像をrole=thumbnailとして登録できる
- [x] #2 既存コミットへのサムネイルの登録、置き換え、削除ができ、置き換え時は作成日時を維持して更新日時を更新する
- [x] #3 元ファイル名、正しいmedia_type、サイズ、作成日時、更新日時を保持する
- [x] #4 画像をPillowでデコード検証し、アニメーション、破損画像、非対応形式、未知のバイナリを拒否する
- [x] #5 2 MiBまたは4096×4096ピクセルを超える画像を明確なエラーで拒否する
- [x] #6 添付を既存objectsストアへ保存し、通常ファイルと重複排除する
- [x] #7 サムネイルを追跡作業ツリーへ影響させず任意の出力ファイルへ安全に取り出せる
- [x] #8 showとJSON出力でサムネイルの有無と全メタデータを確認できる
- [x] #9 gcが参照中のサムネイルを保持し、doctorがサムネイルオブジェクトの欠落と破損を検査する
- [x] #10 READMEを更新し、形式・上限・登録・置換・削除・取得・gc・doctorを自動テストで検証する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Pillowを依存へ追加し、サムネイルのデータ型とPNG・JPEG・WebP静止画像の内容・容量・寸法検証をRepository層へ実装する。 2. commit時登録と既存コミットへの登録・置換・削除・取得をロック付きで実装し、objectsストアを共有する。 3. 参照中オブジェクト判定とdoctorを添付対応し、追跡ファイルを上書きしない原子的なexportを追加する。 4. commit --thumbnail、thumbnail操作、show表示・JSONをCLIへ追加する。 5. Repository/CLIテストとREADMEを更新し全テストを実行する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Pillow 12.3.0を追加し、PNG・JPEG・WebPの静止画像を2 MiB・4096×4096以下でピクセルデコード検証する。commit時登録と既存コミットへの登録・置換・削除・安全なexport、show/thumbnail JSON、objects重複排除、gc/doctor連携を実装した。検証結果: サムネイル対象テスト7件成功、CLIヘルプ表示成功、全テスト113 passed・2 skipped、git diff --check成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
サイズ制限付き静止画像サムネイルをコミット時または後付けで管理できるようにし、objectsストア、show JSON、export、gc、doctorへ統合した。PNG・JPEG・WebPの内容、アニメーション、破損、容量、寸法を検証し、全テスト113件成功・2件スキップで確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
