---
id: TASK-39
title: GUIで音声previewを再生できるようにする
status: To Do
assignee: []
created_date: '2026-07-29 19:47'
labels: []
dependencies:
  - TASK-25
  - TASK-38
priority: low
type: feature
ordinal: 39000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

role=previewへ音声ファイルを保存できても、初期GUIは画像サムネイル表示だけを扱う。音声制作の過去スナップショットをGUIから確認できるよう、コミットを選択したときに音声を再生する専用ビューが必要である。

## ゴール

media_typeがaudio系のpreviewを持つコミットを選択すると、GUI内の音声プレーヤーで安全に再生、停止、シーク、音量調整できるようにする。最初の必須対応形式はWAVとし、実行環境が対応する他形式へ拡張可能な構造にする。

ツリーノード内では自動再生せず、ユーザーがコミットまたはpreviewを選択した後だけ読み込む。未対応コーデックや破損ファイルではGUI全体を失敗させず、ファイル情報と取り出し手段を残す。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 audio/wavのpreviewを持つコミットを選択するとGUI内プレーヤーで再生できる
- [ ] #2 再生、停止、一時停止、シーク、音量調整ができる
- [ ] #3 ツリーノード表示だけでは音声を読み込まず、自動再生しない
- [ ] #4 別のコミットへ移動したときに以前の音声再生と一時リソースが適切に停止・解放される
- [ ] #5 未対応コーデックまたは破損した音声でもGUI全体が失敗せず、元ファイル名、media_type、サイズとexport操作が表示される
- [ ] #6 大きな音声でGUI操作が長時間停止しない
- [ ] #7 READMEが更新され、WAV再生、操作、未対応形式、破損、大容量、リソース解放がテストされる
<!-- AC:END -->
