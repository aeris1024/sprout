---
id: TASK-103
title: GUIから作業ファイルとプレビューを関連アプリで開けるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
updated_date: '2026-10-31 09:30'
labels:
  - gui
  - usability
dependencies:
  - TASK-125.13
references:
  - gui/src/components/SavePanel.tsx
  - gui/src/components/FilePanel.tsx
  - gui/src/components/PreviewPanel.tsx
  - gui/src-tauri/src/lib.rs
  - gui/src-tauri/capabilities/default.json
priority: medium
type: feature
ordinal: 102000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUIには作業ファイルを開く操作や、エクスプローラーで表示する操作がない。画像以外のプレビューは、いったん取り出さないと内容を確認できない。別のアプリで編集して戻る作業の中で、対象のファイルを探す手間が生じる。

対象の境界: 作業ファイルを開く/エクスプローラー表示する操作は、プロジェクト内の対象と安全なパスに限定する。プレビューはTASK-125.13の葉全体の添付資料として、保存した原本をSproutが管理する一時領域へ取り出して関連アプリで開く。この一時領域はプロジェクト外でもよいが、任意の外部パスやリンク先を開ける例外にはしない。
一時原本を外部アプリで編集しても保存済みのプレビューは自動更新しない。既存の置き換え操作と区別し、外部アプリが利用中のファイルを即座に消さず、不要になった一時ファイルの清掃範囲とタイミングを定める。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 未保存の変更と追跡ファイルから、関連アプリで開く操作とエクスプローラーで表示する操作を使える
- [ ] #2 プレビュー原本を管理された一時領域へ取り出し、保存先指定なしで関連アプリから開ける。履歴と作業フォルダを変更せず、外部アプリの利用を妨げずに不要な一時ファイルを清掃できる
- [ ] #3 ファイルがない場合や開けない場合は理由を通知する
- [ ] #4 作業ファイルはプロジェクト内の安全なパスに限定する。プレビューを開くためにSproutが生成した一時原本だけは管理下の外部一時領域を許可し、任意の外部パスやリンク先を開かない
- [ ] #5 自動テストで呼び出しと失敗時の動作を検証し、実機で確認して、gui/README.mdを更新する
<!-- AC:END -->
