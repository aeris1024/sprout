---
id: TASK-11
title: オブジェクトを圧縮して保存する
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:17'
updated_date: '2026-07-28 19:55'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - pyproject.toml
modified_files:
  - pyproject.toml
  - uv.lock
  - src/sprout/repository.py
  - tests/test_repository.py
  - tests/test_cli.py
priority: medium
type: feature
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

大きなバイナリのスナップショット管理という性質上、`.sprout/objects`の肥大が最大の課題(READMEにも記載)。オブジェクトを圧縮して保存すればストレージ効率を大きく改善できる。

## 実装方針

1. 圧縮方式はzstandardを推奨(依存追加: `zstandard`パッケージ)。依存を増やしたくない場合は標準ライブラリの`zlib`でもよいが、大きなバイナリでは速度面でzstdが有利。
2. オブジェクト形式が変わるため`SCHEMA_VERSION`を上げ、metaに圧縮方式(例: `object_compression = zstd`)を記録する。旧バージョンのリポジトリは`check_schema`で明確なエラーにする(マイグレーションを実装する場合は`sprout`起動時ではなく明示的なコマンドで行う)。
3. `_store_object`: 一時ファイルへ圧縮しながら書き込む。ハッシュとサイズは非圧縮の内容に対して計算する(dedupと検証の基準を変えないため)。
4. 読み出し側: `_verify_manifest`と`_materialize`のコピー処理(`shutil.copyfile`)を、伸長しながらハッシュ検証・書き出しを行う共通関数に置き換える。`hash_file`をオブジェクトに使っている箇所(`_store_object`の衝突検証、`_verify_manifest`)は伸長後の内容をハッシュするよう修正する。
5. 既に圧縮済みのファイル(png/jpg/zip等)は圧縮率がほぼ1になる。zstdはその場合でも高速なので特別扱いは不要だが、圧縮レベルは3程度の低めを既定にする。

## 注意

- commit_filesの`size`は非圧縮サイズのまま(復元時の検証・statusの比較に使うため)。
- `_materialize`のステージング(staged/へのコピー)は伸長後の内容を置く。ここを圧縮のまま置くと後段のos.replaceだけで済む設計が壊れるため変更しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 新規リポジトリでオブジェクトが圧縮されて保存される
- [x] #2 commit/restore/switch/statusの動作と結果が非圧縮時と同一である
- [x] #3 ハッシュとサイズは非圧縮内容に基づき、dedupが従来どおり機能する
- [x] #4 旧スキーマのリポジトリを開くと明確なエラーになる
- [x] #5 圧縮・伸長の往復とハッシュ検証がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. スキーマと圧縮方式メタデータを更新する。 2. 非圧縮内容を基準にハッシュ・サイズを算出しながらZstandardレベル3で保存する。 3. 伸長・検証・書き出しを共通化して検証と復元を置き換える。 4. 圧縮、重複排除、復元、破損検出、旧スキーマ拒否をテストする。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Zstandardレベル3を採用し、スキーマ2とobject_compression=zstdを記録。既存互換性は本格運用前のため対象外。検証: uv run pytest（88 passed, 2 skipped）。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
オブジェクトを非圧縮内容のSHA-256とサイズを維持したままZstandardで保存するよう変更した。伸長・ハッシュ検証・書き出しを共通化し、restore、doctor、重複排除時の検証へ適用。旧スキーマは期待値を含む明確なエラーで拒否し、圧縮往復とメタデータを自動テストで確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
