---
id: TASK-25
title: GUIにコミットツリーのサムネイル付き俯瞰ビューを実装する
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:28'
updated_date: '2026-08-09 06:31'
labels: []
dependencies:
  - TASK-21
  - TASK-22
  - TASK-23
modified_files:
  - README.md
  - gui/README.md
  - gui/src/App.tsx
  - gui/src/App.css
  - gui/src/App.test.tsx
  - gui/src/components/CommitTree.tsx
  - gui/src/lib/sprout.ts
  - gui/src/lib/graph.ts
  - gui/src/lib/graph.test.ts
  - gui/src/lib/thumbnails.ts
  - gui/src/lib/thumbnails.test.ts
  - gui/src-tauri/src/lib.rs
  - gui/src-tauri/Cargo.toml
  - gui/src-tauri/Cargo.lock
priority: medium
type: feature
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

リポジトリ全体をツリー構造で俯瞰し、各コミットの画像サムネイルを一目で確認できるビューを作る。初期実装は履歴の俯瞰と静止画像サムネイルの高速表示に集中する。音声、動画、アニメーション画像、3Dモデル等のクリック時プレビューは独立した後続タスクで追加する。

## ゴール

全ブランチのコミットを親子関係付きのツリーまたはグラフとして表示し、role=thumbnailの静止画像をコミットノードへ表示する。コミット数が多い場合も実用的に操作でき、現在のブランチ先端と選択中コミットを識別できること。

ノード選択ではコミット詳細を表示し、既存のGUI操作基盤を通じてrestore、switch、サムネイル登録へ移動できるようにする。サムネイル取得結果はコミットIDと添付情報を基準にキャッシュし、不要な再取得を抑える。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 全ブランチと削除済みブランチ由来のコミットが親子関係付きのツリーまたはグラフとして表示される
- [x] #2 role=thumbnailの静止画像が対応するコミットノードへ表示される
- [x] #3 初期実装は音声、動画、アニメーション画像、3Dモデルをツリーノード内で自動再生または描画しない
- [x] #4 ノード選択でコミット詳細が表示される
- [x] #5 ツリーからrestore、switch、画像サムネイル登録の操作へ移動できる
- [x] #6 現在のブランチ先端と選択中コミットが視覚的に区別できる
- [x] #7 コミット数が多い履歴でも実用的にスクロール、折りたたみ、または省略表示できる
- [x] #8 サムネイルがキャッシュされ、添付が変更されていない場合の再取得が抑制される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. tree --jsonのコミット・ブランチ・タグ・添付契約をTypeScript型へ追加し、親子関係を循環なく反復的に表示行へ変換する。 2. GUIへツリータブを追加し、ブランチ先端・現在先端・選択状態、折りたたみと段階表示、コミット詳細とrestore/switch/thumbnail登録導線を実装する。 3. Rust IPCでCLI thumbnail --outputをOS一時領域へ安全に実行して静止画像data URLを返し、フロントエンドでcommit ID・object hash・media type単位の遅延キャッシュを実装する。 4. ツリー構築、キャッシュ、操作導線、Rust変換のテストを追加し、React/Rust/Python回帰テスト、Tauri build、Playwright実画面確認を行う。 5. GUI操作文書を更新し、客観的証拠に基づいて受入条件を完了する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
tree --jsonを反復的に親子行へ変換し、削除済みブランチ由来を含む全コミット、ブランチ先端、タグを表示するツリータブを実装した。PNG・JPEG・WebPのthumbnailだけをIntersectionObserverで遅延取得し、project・commit ID・object hash・media typeキーのLRUメモリキャッシュと同時要求の重複排除を追加した。Rust IPCはCLI thumbnail --outputをOS一時領域へ実行し、2 MiB以下の検証済み静止画をdata URLへ変換するためGUIは.sproutを直接読まない。80件単位の追加表示、内部スクロール、子ツリー折りたたみ、選択詳細、restore・switch・thumbnail登録導線を追加した。検証: frontend 21 tests passed、TypeScript/Vite build成功、Rust 4 tests passed、Python 133 passed・2 skipped、Tauri release build成功。Playwrightで1280pxと900pxの分岐・削除済み由来・サムネイル・選択・折りたたみを確認しconsole error 0件、狭幅の横はみ出しを検出して1180px以下の縦積みに修正した。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
全履歴を親子関係付きで俯瞰できるサムネイル付きコミットツリーをGUIへ追加した。静止画限定の遅延・キャッシュ取得、先端・選択表示、折りたたみ・段階表示、詳細とrestore/switch/thumbnail操作を、自動テスト21件、Rust/Python回帰、Tauri build、Playwright実画面確認で検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
