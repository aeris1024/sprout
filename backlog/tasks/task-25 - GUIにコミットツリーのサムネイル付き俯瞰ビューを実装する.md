---
id: TASK-25
title: GUIにコミットツリーのサムネイル付き俯瞰ビューを実装する
status: To Do
assignee: []
created_date: '2026-07-15 16:28'
labels: []
dependencies:
  - TASK-21
  - TASK-22
  - TASK-23
priority: medium
type: feature
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

リポジトリ全体をツリー構造で俯瞰し、各コミットのサムネイルを一目で見られるビューを作る。GUI構想の中心機能。

## 実装方針

1. **データ取得**: `sprout tree --json`(TASK-22)で全コミット・親子関係・ブランチ・サムネイル有無を取得し、フロント側で`parent_id`から子リストを組み立てる。
2. **レイアウト**: 分岐はブランチごとのレーン(gitグラフ風)またはノードツリーで描画する。コミット数が多くても破綻しないよう、仮想スクロールか折りたたみ(古い直線区間の省略)を検討する。描画は自前SVG/Canvasでも、React Flow等のグラフライブラリでもよい(実装時に選定)。
3. **サムネイル表示**: サムネイルを持つコミットはノードに画像を表示する。バイト列の取得は`sprout thumbnail export COMMIT <一時ファイル>`で書き出してから読み込む方式が単純(Tauriのassetプロトコルまたは`convertFileSrc`で表示)。取得結果はコミットIDをキーにアプリ内キャッシュし、毎回exportしない。
4. **音声サムネイル**: media_typeがaudio系(wav等)の場合は再生ボタン付きノードにする。Web Audio APIまたは`<audio>`要素で再生する。余力があれば波形の簡易描画も行う。
5. **操作連携**: ノード選択で詳細パネル(`show --json`の内容+サムネイル拡大表示)、右クリック等から`restore`/`switch`/サムネイル登録(`thumbnail set`)を呼べるようにする。破壊的操作の確認フローはTASK-24と共通化する。
6. **現在地の表示**: HEADブランチの先端を強調表示する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 全ブランチのコミットがツリー(グラフ)として描画される
- [ ] #2 サムネイル付きコミットのノードに画像が表示される
- [ ] #3 音声サムネイル(wav等)がGUI上で再生できる
- [ ] #4 ノード選択でコミット詳細が表示される
- [ ] #5 ツリーからrestore/switch/サムネイル登録が行える
- [ ] #6 現在のブランチ先端が視覚的に区別できる
- [ ] #7 サムネイルがキャッシュされ再取得が抑制される
<!-- AC:END -->
