---
id: TASK-58
title: 芽のマップでスナップショットとブランチを表示する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-27 15:03'
updated_date: '2026-10-27 19:23'
labels:
  - gui
  - gui-redesign
dependencies:
  - TASK-57
  - TASK-52
references:
  - gui/design/sprout-map-mockup.html
  - gui/src/components/CommitTree.tsx
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: medium
type: feature
ordinal: 58000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

GUI刷新（doc-1、TASK-51で承認済み）では、現在のインデント付きツリー表示をやめ、下から上へ茎が伸びる「芽のマップ」で全スナップショットを俯瞰する。

## ゴール

全スナップショットを、古いものが下、新しいものが上になるよう茎と葉で描画する。ブランチは茎の途中から分かれる枝として描き、サムネイル・タグ・現在位置を表示する。葉を選ぶと詳細パネルに選択状態が伝わる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 古いスナップショットが下、新しいものが上に並び、茎が下から上へ伸びる
- [x] #2 スナップショットが葉として茎の左右に交互に付き、サムネイルとメッセージが表示され、サムネイルがない葉は同じ大きさの無地で表示される
- [x] #3 ブランチが分岐元から分かれて上へ伸びる枝として描かれ、削除済みブランチ由来のスナップショットも欠けずに表示される
- [x] #4 ブランチ名が枝の先、タグが葉の札として表示され、現在のブランチが強調される
- [x] #5 TASK-52の現在位置が青い枠で示され、開いた直後と更新後に現在位置が見える位置へスクロールする
- [x] #6 葉をクリックまたはキーボードで選択でき、選択が詳細パネルへ伝わる
- [x] #7 数百件のスナップショットでも表示とスクロールが滞らず、サムネイルは表示範囲に近いものから読み込まれる
- [x] #8 スナップショットが多い場合に拡大・縮小または古い区間の折りたたみで全体を把握できる
- [x] #9 旧コミットツリー表示が削除され、レイアウトと選択のテストがある
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 実装と検証（2026-10-28）
- lib/sproutMap.tsにレイアウト（古いものが下、作成ブランチごとのレーン、茎の左右交互の葉、分岐元からの枝、枝先ラベル、タグ、つぼみの紐づけ、現在位置）を実装。同じ秒に作られたコミットはCLIの並びを保ち、親を必ず子より下に置く（反復処理で長い履歴でも再帰しない）。
- components/SproutMap.tsx（SVG）で描画。葉はrole=buttonでクリック/Enter/Spaceで選択、サムネイルはIntersectionObserverで表示範囲付近から読み込み、50〜150%の拡大縮小、現在位置への自動スクロール（スクロール領域の大きさが確定してから実行）。
- 選択した葉の詳細はcomponents/CommitPanel.tsxとして右パネルへ移動。旧CommitTree・lib/graph.tsとそのテストを削除。
- 検証: pnpm test 31 passed（レイアウト単体テスト6件、キーボード選択・拡大縮小・パネル切り替えのテストを追加）、tsc成功。実CLIで作ったリポジトリのtree出力を使い、Vite上でマップ表示・枝・タグ・現在位置の中央表示・詳細パネル・375px幅で右パネルが下へ移ることを確認。500件のレイアウトは200ms未満。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
旧ツリー表示を芽のマップに置き換えた。古いスナップショットが下・新しいものが上に並び、葉にサムネイル、枝先にブランチ名、葉にタグ、現在位置に青い枠を表示する。キーボード選択、拡大縮小、表示範囲付近からのサムネイル読み込み、現在位置への自動スクロールに対応し、選択した葉の詳細は右パネルに表示する。GUIテスト31件と実データを使ったブラウザ確認で検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
