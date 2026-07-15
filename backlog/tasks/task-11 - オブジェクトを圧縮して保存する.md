---
id: TASK-11
title: オブジェクトを圧縮して保存する
status: To Do
assignee: []
created_date: '2026-07-15 16:17'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - pyproject.toml
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
- [ ] #1 新規リポジトリでオブジェクトが圧縮されて保存される
- [ ] #2 commit/restore/switch/statusの動作と結果が非圧縮時と同一である
- [ ] #3 ハッシュとサイズは非圧縮内容に基づき、dedupが従来どおり機能する
- [ ] #4 旧スキーマのリポジトリを開くと明確なエラーになる
- [ ] #5 圧縮・伸長の往復とハッシュ検証がテストで検証されている
<!-- AC:END -->
