---
id: TASK-40
title: GUIでアニメーション画像と動画previewを再生できるようにする
status: To Do
assignee: []
created_date: '2026-07-29 19:47'
updated_date: '2026-10-27 15:05'
labels: []
dependencies:
  - TASK-38
  - TASK-59
priority: low
type: feature
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

role=previewへアニメーション画像や動画を保存できても、初期GUIは静止画像サムネイルだけを扱う。制作途中の動きや動画化した成果を、コミットを選択したときにGUI内で確認できる専用ビューが必要である。

## ゴール

アニメーションGIF等のアニメーション画像と、実行環境が安全にデコードできる代表的な動画previewを、葉を選択した後の詳細パネルで再生できるようにする。芽のマップの葉では静止画像サムネイルだけを表示し、重いpreviewは自動取得・自動再生しない。

未対応コーデックや破損ファイルは汎用ファイル表示へフォールバックし、元データを取り出せる状態を維持する。動画からGIF等の軽量previewを生成する機能は、この再生機能と分離して後から追加できること。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 image/gif等の対応するアニメーション画像previewをコミット詳細で再生できる
- [ ] #2 実行環境が対応する代表的なvideo系media_typeをコミット詳細で再生、一時停止、シークできる
- [ ] #3 別のコミットへ移動したときに以前の再生と一時リソースが停止・解放される
- [ ] #4 未対応コーデックまたは破損ファイルでもGUI全体が失敗せず、ファイル情報とexport操作へフォールバックする
- [ ] #5 大きな動画でGUI操作が長時間停止しない
- [ ] #6 READMEが更新され、アニメーション画像、動画操作、未対応形式、破損、大容量、リソース解放がテストされる
- [ ] #7 芽のマップの葉ではpreviewを自動取得・自動再生せず、role=thumbnailの静止画像だけを表示する
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TASK-51のGUI刷新設計（doc-1）に合わせ、ツリービュー前提の記述を芽のマップと詳細パネルへ更新した。
<!-- SECTION:NOTES:END -->
