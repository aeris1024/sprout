---
id: TASK-70
title: 非対応のオブジェクトencodingを読み出し・再利用時に拒否する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-28 19:46'
updated_date: '2026-10-28 20:00'
labels: []
dependencies:
  - TASK-67
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - tests/test_v1_storage.py
  - tests/test_cli.py
  - README.md
priority: medium
type: bug
ordinal: 70000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

TASK-67でobjects.encodingを保存し、doctorは非対応値を検出するようになった。一方、通常の読み出しは常にzstdと仮定しており、encodingを非対応値へ変更しても実体がzstdなら復元が通るケースを再現した。オブジェクトの再利用でも、対応可否の確認が必要である。

## ゴール

復元・export・cat・添付取得などの読み出し、および保存済みオブジェクトの再利用時にencodingを確認し、非対応値は明示的なエラーで拒否する。エラーでは対象の内容ハッシュとencodingを特定でき、既存のCLI・JSONのエラー処理に対応する。

拒否時に作業ファイル・既存の出力先・保存済み参照を意図せず変更しない。doctorによる診断と、現在対応しているzstdの正常系を維持する。

## 対象範囲

通常操作での拒否、診断、テスト、互換性方針の文書化を含める。将来の保存形式追加時には、DBスキーマ変更の有無とは別に、以前のCLIで安全に読み書きできるかを判断する。

新しい圧縮方式、無圧縮保存、分割保存は実装しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 復元・export・cat・添付取得などで非対応encodingをzstdと仮定して読み出さず、明示的なエラーを返す
- [x] #2 保存済みオブジェクトを再利用する書き込み操作でも、非対応encodingを検出して拒否する
- [x] #3 拒否時に作業ファイル・既存の出力先ファイル・保存済み参照を意図せず変更せず、対象の内容ハッシュとencodingを特定できる
- [x] #4 doctorによる非対応encodingの診断と、対応するzstdの正常な読み出し・再利用を維持する
- [x] #5 非対応encodingの復元・取得・再利用での拒否、失敗時の非変更、CLI・JSONのエラー、zstdの正常系を自動テストで検証する
- [x] #6 将来の保存形式追加ではスキーマ変更の有無とは別に互換性を判断する方針を文書化し、新しい圧縮方式や分割保存は追加しない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. objects.encodingの共通検証を読出しと再利用・参照登録に適用する。2. 非対応形式では出力・作業ファイル・参照を変更せず構造化エラーを返す。3. doctorと正常zstdを含む回帰テストとREADMEを追加する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
objects.encodingの共通チェックを通常読出し・物理ファイル再利用・参照登録へ追加。unsupported_object_encodingのdetailsにobject_hashとencodingを含める。go等は退避つぼみの作成前に対象形式を確認する。全体/部分復元・go・export・cat・commit・つぼみ保存・参照登録・thumbnail取得/再利用で拒否と履歴DB/作業ファイル/既存出力の非変更を検証。CLIとJSONの実エラー経路、doctor、正常zstdも検証。READMEに形式互換性をスキーマとは別に判断する方針を追記。全Python335テスト成功・19スキップ（環境依存）。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
非対応encodingを読出し・再利用前に構造化エラーで拒否し、ファイルと保存済み参照を保持。doctor・zstd・CLI/JSONを含む全Python335テスト成功で検証。
<!-- SECTION:FINAL_SUMMARY:END -->
