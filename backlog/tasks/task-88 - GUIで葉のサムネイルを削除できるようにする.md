---
id: TASK-88
title: GUIで葉のサムネイルを削除できるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-30 17:34'
updated_date: '2026-11-01 05:24'
labels:
  - gui
dependencies:
  - TASK-125.12
  - TASK-126
references:
  - src/sprout/cli.py
  - gui/src/App.tsx
  - gui/src/lib/thumbnails.ts
  - gui/README.md
priority: medium
type: feature
ordinal: 87000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
既存の葉サムネイル削除機能をGUIから使えるようにする。CLI再編後はTASK-125.12のleaf thumbnail deleteを正規の呼び出し先とする。
TASK-126の補助メニューと整合する入口から削除できるようにし、同じ操作のために詳細上部へ常時ボタンを増やさない。サムネイルがある場合だけ表示し、削除確認・キャンセル・失敗通知・表示更新を扱う。サムネイルの削除と葉そのものの削除を区別し、葉の削除に固有のタグ保護制限をサムネイル削除へ流用しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 サムネイルがある葉の詳細から削除でき、サムネイルがない葉には削除操作が表示されない
- [x] #2 削除前に確認が表示され、キャンセルすると何も変更しない
- [x] #3 削除後はマップと葉の詳細に古いサムネイルが残らない
- [x] #4 失敗時は理由を通知し、サムネイルの表示を変更しない
- [x] #5 自動テストで削除、キャンセル、失敗時の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. サムネイルありの葉だけ補助メニューにサムネイル削除を表示し、葉自体の削除やタグ制限と分離する。 2. 確認後に正規leaf thumbnail deleteを呼び、キャンセル/失敗は表示を維持する。 3. 成功時はマップと詳細を更新し、削除/キャンセル/拒否/タグ付きの自動テストと実CLIの画面検証を行いREADMEを更新する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
全GUI284テスト・ビルド成功。CLI全体759 passed/20 skipped。実CLIとAppをつないだブラウザーで、タグ付き葉のキャンセルと削除、マップ画像2→1枚、葉2件・タグ・生成元・作業ファイルの維持、削除後メニュー非表示を検証。TauriネイティブIPCは検証用ブリッジに置換。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
サムネイルありの葉だけ補助メニューから確認付きで削除できる。タグ付き葉の削除制限と分離し、キャンセル/拒否は表示を維持、成功時はマップと詳細を更新。GUI284テスト、CLI759 passed/20 skipped、ビルドと実CLI画面連携で検証。
<!-- SECTION:FINAL_SUMMARY:END -->
