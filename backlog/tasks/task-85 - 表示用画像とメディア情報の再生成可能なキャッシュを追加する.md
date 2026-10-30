---
id: TASK-85
title: 表示用画像とメディア情報の再生成可能なキャッシュを追加する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-29T20:09:00Z'
updated_date: '2026-10-30 16:19'
labels: []
dependencies:
  - TASK-79
references:
  - src/sprout/preview_image.py
  - gui/src/components/PreviewImage.tsx
  - gui/src/lib/thumbnails.ts
  - src/sprout/cache.py
  - tests/test_previews.py
  - gui/src/components/PreviewImage.test.tsx
  - gui/README.md
priority: medium
type: enhancement
ordinal: 84000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
静止画像previewは表示のたびに原本を一時展開してデコード・縮小し、表示用PNGを生成している。繰り返し閲覧時の待ち時間と処理負荷を減らすため、表示用画像と取得済みの画像寸法・形式などを再利用する。キャッシュは原本から再生成できる派生データとし、履歴の必須データにはしない。既存の作業ツリーハッシュキャッシュやマップ用サムネイルキャッシュとは役割を区別する。初期対象は実装済みの静止画像とその情報で、音声・動画・3D用デコーダや再生機能の追加はTASK-39・40・41で扱う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 同じ原本と表示条件の静止画像を再表示すると、生成済み表示用画像と画像情報を利用できる。対象を選ぶまでは原本の取得・デコードを開始しない
- [x] #2 キャッシュの同一性に原本ハッシュ、生成処理のバージョン、表示サイズ等の条件を反映し、添付の置き換えや条件変更後に古い画像・メディア情報を表示しない。プロジェクト間でも誤った原本を参照しない
- [x] #3 キャッシュの欠落・削除・破損・生成中断・保存失敗は原本や履歴を壊さず、安全に再生成またはエラー表示できる。失敗した生成物を完成済みキャッシュとして再利用しない
- [x] #4 キャッシュ容量の上限と破棄・清掃の規則を定義し、使用中の表示や同時生成と整合する。キャッシュ削除で原本objectsや復旧用データを削除しない
- [x] #5 キャッシュは履歴復元・バックアップの必須要素にせず、存在しない環境でも閲覧を再開できる。原本DB変更の必要性は実装時に判断し、変更する場合はTASK-80の形式・互換性方針に従う
- [x] #6 キャッシュヒット時に再生成しないこと、原本/条件/生成処理バージョン変更、破損、容量超過、同時要求、中断・保存失敗と清掃後の再生成を自動テストで検証し、保存場所と消去手順をREADMEに記載する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implement the approved optional per-project .sprout/preview-cache with a 256 MiB completed-entry limit and 32 MiB per-entry limit, leaving history schema V7 unchanged. Cache selected static image PNG results and original format/dimensions using source hash, processing/decoder version, display/validation conditions, project and object fingerprint. Validate checksums/PNG metadata, regenerate corrupt or missing entries, and fall back to normal rendering on storage/locking failures. Publish atomically under a nonblocking project cache writer lock, evict oldest-used complete entries, clean abandoned pending files, preserve displayed in-memory results, and document cleanup/backup rules. Verify lazy loading, hit avoids original export/decode, replacements and condition/version changes, project isolation, corruption, failed storage, quota/LRU, concurrent generation, interruption and original encoding/missing-object protection. Run complete Python/GUI regressions, type checks and production client build before integration.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User approved combined policy; TASK-83 and TASK-84 are complete and integrated. Implement the approved disposable per-project 256 MiB static image/media cache without changing schema V7.

Implemented disposable JSON cache entries containing generated PNG data and media metadata, keyed by source/processing/Pillow/display/project/object identity. Cache failures leave originals/history unchanged and return the normal decoded result. Added checksum/PNG metadata validation, atomic publication, nonblocking cross-process writer lock, LRU eviction and abandoned pending-file cleanup. Cache hits skip original export/decompression/decode while retaining encoding and missing-object checks; no history DB changes. Fixed Windows mtime API fallback so reuse actually updates LRU timestamps. GUI displays cached source format alongside dimensions and keeps lazy selection behavior. Added 15 cache tests and a GUI metadata/lazy-loading case. Final complete state including TASK-83/84: Python 518 passed, 19 skipped (227.34s); GUI full 109 passed; TypeScript noEmit, Vite production build and git diff --check passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Cache selected static previews and media metadata in an optional per-project bounded store without changing V7 history data. Regenerate missing/corrupt results, handle storage failure safely, serialize publication/cleanup and enforce LRU limits on Windows. Document cleanup and backup behavior. Verified full final suite: 518 Python tests passed with 19 platform skips, 109 GUI tests, type checks and production client build.
<!-- SECTION:FINAL_SUMMARY:END -->
