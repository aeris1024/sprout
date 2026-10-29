---
id: TASK-68
title: GUIの芽のマップを日時ではなくコミットの作成順で配置する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-28 19:46'
updated_date: '2026-10-28 19:58'
labels: []
dependencies:
  - TASK-67
references:
  - gui/src/lib/sproutMap.ts
  - gui/src/lib/sproutMap.test.ts
  - src/sprout/cli.py
priority: medium
type: bug
ordinal: 68000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

TASK-67でバックエンドのコミット一覧はseqに基づく作成順になったが、GUIの芽のマップはcreated_atで並べ替え直している。時計を巻き戻して分岐先を保存すると、作成順がA→B→CでもマップではA→C→Bになるケースを再現した。

## ゴール

バックエンドが返す作成順をGUIでも尊重し、時計の巻き戻りや同一日時、複数ブランチでも一貫した配置にする。親を子より先に配置する性質を維持する。

既存JSONのコミット配列順を利用し、保存スキーマや公開フィールドの追加は行わない。日時は表示用の情報として維持する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 バックエンドが返すseqに基づくコミット配列順を尊重し、芽のマップでcreated_atによる並べ替え直しを行わない
- [x] #2 時計の巻き戻り、同一日時、複数ブランチでも作成順を維持し、親コミットを子コミットより先に配置する
- [x] #3 作成順A→B→Cが時計の巻き戻りでA→C→Bになる再現ケースと、同一日時・分岐・親子関係をGUIテストで検証する
- [x] #4 既存JSONの配列順で対応し、保存スキーマ・公開フィールド・日時表示の仕様を追加変更しない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. JSONのコミット配列を逆順にして作成順を起点に配置し、既存の親子関係の補正を維持する。2. 時計の巻き戻り・同一日時・複数ブランチ・親子関係のGUI回帰テストを追加する。3. GUIテストと型チェック・ビルドで検証する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
GUIの配列を作成順に反転し、親を先に置く補正を維持。時計巻き戻り・同時刻・分岐・親子順序の3件を追加。GUI全54テスト成功、tsc --noEmitとvite build成功。保存スキーマ・JSON型・日時表示に変更なし。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
日時による再ソートを除き、バックエンドの作成順で芽のマップを配置。GUI 54テスト・型チェック・ビルドで検証済み。
<!-- SECTION:FINAL_SUMMARY:END -->
