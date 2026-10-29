---
id: TASK-79
title: GUI内で静止画像のpreviewを選択して表示できるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-29T17:14:00Z'
updated_date: '2026-10-29T17:20:00Z'
labels: []
dependencies:
  - TASK-72
references:
  - gui/src/components/PreviewPanel.tsx
  - src/sprout/cli.py
priority: high
type: feature
ordinal: 78000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
previewの管理はGUIにあるが、静止画像の内容を見るには毎回外部へ取り出す必要がある。葉の詳細で選んだ画像を読み取り専用で表示し、保存内容をGUI内で確認できるようにする。音声・動画・アニメーション・3Dは既存の別タスクで扱う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 葉の詳細で画像previewを選択するとPNG・JPEG・静止WebP・BMPをGUI内で表示でき、一覧だけでは画像本体を取得しない
- [x] #2 別の添付・コミット・プロジェクトへの切り替え、置き換え、削除時に古い画像と遅延応答を残さず、表示を閉じられる
- [x] #3 破損・未対応・アニメーション・大容量画像はGUIを停止させず理由を表示し、取り出し操作を維持する
- [x] #4 画像表示は作業ファイルとpreview原本を変更せず、一時ファイルを清掃する
- [x] #5 自動テストと操作説明が更新され、GUIビルドが成功する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 既存Pillowを使い、CLI preview imageで選択添付を検証・縮小してPNGとして返す。入力20 MiB・1600万画素・一辺8192pxに制限し、表示用は最大2048pxに縮小、原本を変更しない。2. 詳細パネルに画像表示/閉じるを追加し、選択対象だけ取得する。コミット・プロジェクト・添付ハッシュを表示キーにして古い応答を無視する。3. 画像形式・破損・アニメーション・サイズ制限・一時ファイル清掃とGUIの切替/エラーをテストし、説明とビルドを検証する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
検証: CLI全体390 passed / 19 skipped、追加画像処理テスト8件成功、GUI101件成功、TypeScript + Vite build成功。実画像4形式のデコード・画素内容・縮小・原本/作業ファイル不変、破損/非対応/アニメーション/上限超過と一時ファイル清掃を検証。DOMテストで選択時だけの取得・表示/閉じる・別添付の遅延応答無視・ハッシュ/削除/コミット/プロジェクト切替・失敗/再試行/取り出し維持を検証。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
プレビュー一覧の「画像を表示」から静止画像をGUI内で確認できるようにした。PNG/JPEG/静止WebP/BMPを既存Pillowで検証し、CLI preview image経由で表示用PNGを返す。選択時だけ読み込み、切替や置換・削除では古い表示を破棄する。入力20 MiB/一辺8192px/1600万画素、表示は長辺2048px以内。原本は変更せず、非対応・破損・上限超過では理由と取り出し手段を残す。
<!-- SECTION:FINAL_SUMMARY:END -->
