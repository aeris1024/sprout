---
id: TASK-110
title: パスの大文字小文字とUnicode表記の違いによる衝突を履歴に入れないようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 18:06'
updated_date: '2026-10-30 18:40'
labels:
  - storage
  - v1
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - README.md
priority: high
type: bug
ordinal: 109000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Windowsで`Logo.png`をエクスプローラーで`logo.png`へ改名すると`status`は変更なしのままで、`sprout track logo.png`して保存すると、1つのファイルが別の素材IDを持つ2つのパスとしてコミットに記録される。以後は`go`が前の版にも最新版にも「restore recovery conflict」で失敗し、`export`も失敗するが、`status`と`doctor`は正常と表示する。一度入ったコミットはWindowsで正しく展開できず、後から修復できない。`sprout move A.txt a.txt`も「移動先が既に存在する」と拒否され、正しい改名手段がない。NFDのパスも正規化されずに保存される。アプリは未運用のため、V1の保存形式を直接変更してよい。形式番号は1のままとし、旧構造からの移行は用意しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 追跡パス、コミットのファイル、つぼみのファイルのいずれでも、NFC正規化と大文字小文字の同一視で同じになるパスをDBの制約で保存できない
- [x] #2 衝突するパスの登録はOSを問わず拒否され、対象のパスと理由を含むエラーになる。作業ファイルと履歴は変更しない
- [x] #3 `sprout move`で大文字小文字や表記だけの改名ができ、素材IDを維持し、改名前後の履歴がつながる
- [x] #4 外部で大文字小文字だけを改名した場合に`status`で検出でき、素材IDを維持して記録できる
- [x] #5 保存時の表記（大文字小文字など）は表示と復元で維持される
- [x] #6 `doctor`が衝突するパスを検出する
- [x] #7 自動テストで改名、衝突、つぼみ、復元、export、NFDのパスを検証し、README.mdとV1のスキーマ検査を更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add path_key (NFC + casefold) to tracked_paths, commit_files and bud_files with per-scope uniqueness. 2. Reject colliding paths and file/folder collisions on every OS. 3. track, move and commit keep the file ID for spelling-only renames; status and diff report renamed. 4. Restore treats spelling-only differences as renames. 5. doctor validates keys. 6. Tests and docs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
path_key = NFC + casefold, unique per scope. Colliding spellings and file/folder collisions rejected on every OS. External spelling changes appear as renamed in status/diff and are adopted when saving or restoring, keeping the file ID. Full restores also respell kept folders. Untrack is now case-insensitive on every OS.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Paths are now identified by path_key so spelling variants cannot enter history; move, track and external spelling renames keep the file ID. Verified with tests/test_path_keys.py, the original go/export failure reproduced through the real CLI, 537 pytest passes, GUI tests and build.
<!-- SECTION:FINAL_SUMMARY:END -->
