---
id: TASK-41
title: GUIでSTL等の3Dモデルpreviewを表示できるようにする
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
ordinal: 41000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

role=previewへ3Dモデルを保存できても、初期GUIは静止画像サムネイルだけを扱う。過去コミットの形状を外部アプリへ毎回書き出さず確認できるよう、コミット選択時に利用する3Dビューアーが必要である。

## ゴール

最初の必須対応形式をSTLとして、コミット詳細でモデルを読み込み、回転、パン、ズーム、表示リセットできる3Dビューを提供する。将来GLB等の単一ファイル形式を追加できる構造とし、複数の関連ファイルを必要とする形式は初期範囲に含めない。

モデルはユーザーが葉を選択して詳細パネルを開いた後だけ読み込む。極端に大きいモデル、破損モデル、未対応形式ではGUI全体を失敗させず、ファイル情報と取り出し手段を表示する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 model/stlまたは対応するSTL media_typeのpreviewをコミット詳細で3D表示できる
- [ ] #2 モデルの回転、パン、ズーム、表示リセットができる
- [ ] #3 別のコミットへ移動したときに以前の3D表示とGPU・一時リソースが解放される
- [ ] #4 破損モデル、未対応形式、過大なモデルでもGUI全体が失敗せず、ファイル情報とexport操作へフォールバックする
- [ ] #5 STL以外の単一ファイル3D形式を後から追加でき、複数関連ファイル必須形式は初期対応外として明記される
- [ ] #6 READMEが更新され、STL表示、操作、破損、未対応形式、過大モデル、リソース解放がテストされる
- [ ] #7 芽のマップの葉の表示だけでは3Dモデルを読み込まず、ユーザーが葉を選んで詳細パネルを開いた後に読み込む
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TASK-51のGUI刷新設計（doc-1）に合わせ、ツリービュー前提の記述を芽のマップと詳細パネルへ更新した。
<!-- SECTION:NOTES:END -->
