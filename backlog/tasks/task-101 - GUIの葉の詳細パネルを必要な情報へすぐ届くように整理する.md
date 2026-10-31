---
id: TASK-101
title: GUIの葉の詳細パネルを必要な情報へすぐ届くように整理する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 17:54'
updated_date: '2026-10-31 05:57'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/CommitPanel.tsx
  - gui/src/App.css
  - gui/README.md
priority: medium
type: enhancement
ordinal: 100000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
葉の詳細パネルは縦に長く、サンプルで高さ2,388pxあり、メモは2,023pxの位置にある。よく使うメモやラベルへ大きくスクロールする必要がある。幅は320px固定で、ファイル名やメッセージが読みにくい。幅700pxの画面ではマップの高さが198pxまで狭くなる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 メモ・ラベル・タグ、プレビュー、保存済みファイルへ大きくスクロールせずに移動できる
- [x] #2 移動や枝の作成など主要な操作が、詳細の先頭付近から使える
- [x] #3 パネルの幅を変更でき、再起動後も維持される。マップが操作不能な幅にならない
- [x] #4 狭いウィンドウでもマップとパネルの両方を実用的な大きさで操作できる
- [x] #5 自動テストで既存の操作が引き続き使えることを検証し、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 葉の詳細の順序を、主要操作→移動リンク→情報→メモ・ラベル・タグ→プレビュー→保存済みファイルへ変える
2. 固定表示の移動リンクで各節へすぐ移動できるようにする
3. マップとパネルの間に幅変更の分割線（ポインタ・キーボード）を置き、幅を設定へ保存する。マップは360pxを下回らせない
4. 狭いウィンドウでは660pxまで左右に並べ、それ未満は上下に積んで両方の最小の高さを保つ
5. 自動テストとブラウザ実機で確認し、gui/README.mdを更新する
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
メモの位置は実画面で2,023px相当から593pxへ移動し、固定の移動リンクで各節へ1クリックで届く。幅700×高さ600ではマップ360×413、パネル334幅を確認（以前はマップの高さ198px）。幅560では上下に積み、マップ217・パネル248の高さを確認。分割線はドラッグ上限で panel 634/map 360、下限で panel 280、再読み込み後も460を維持することをCLI接続の開発画面で確認。Tauri窓のminWidthは840のままで、狭い幅はブラウザ表示で確認した。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
葉の詳細を主要操作→固定の移動リンク→情報→メモ・ラベル・タグ→プレビュー→保存済みファイルの順に整理し、パネル幅を変更・保存できる分割線を追加した。狭い幅では660pxまで左右に並べ、それ未満は上下に積む。自動テスト186件成功、型チェック成功、CLI接続の開発画面で幅700・560と分割線の上下限・再読み込みを確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
