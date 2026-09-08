---
id: TASK-49
title: 復元時のパス保護とファイル構成変更に対応する
status: Done
assignee:
  - '@codex'
created_date: '2026-09-08 10:35'
updated_date: '2026-09-08 10:54'
labels: []
dependencies: []
modified_files:
  - src/sprout/repository.py
  - tests/test_repository.py
  - tests/test_restore_safety.py
  - README.md
priority: high
type: bug
ordinal: 49000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
restore、switch、branch --switchと巻き戻し・起動時復旧を保護する。リンク経由の外部上書きを拒否し、全体復元のファイルとディレクトリの入れ替えに対応する。部分復元は選択外へ拡張しない。GUIのパス問題は対象外。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 リンク・ジャンクション・境界外パスを変更前に拒否し、外部データを保持する
- [x] #2 全体復元でファイルとディレクトリの入れ替えが双方向に成功する
- [x] #3 未追跡エントリと部分復元の選択外ファイルを保護する
- [x] #4 失敗・中断・再中断から安全に復旧し、旧計画を読み取れる
- [x] #5 構造化CLIエラー、Windows実ジャンクション、失敗注入をテストしREADMEを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add shared path validation before reads and filesystem changes. 2. Plan topology changes and persist versioned recovery data. 3. Implement repeatable rollback and safe legacy recovery. 4. Test junctions, scope conflicts, failure injection and CLI JSON. 5. Run Python tests and update README.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
実装: リンク・ジャンクションと境界検査、全体復元の双方向構成変更、部分復元の範囲拒否、固定サイズ進捗記録、再中断可能な巻き戻し、旧計画の安全な変換を追加。Windows実ジャンクションとUbuntu/Python 3.12で回帰検証中。GUIには変更なし。

最終検証: Windows/Python 3.14で201 passed, 19 skipped。Ubuntu/Python 3.12.14で203 passed, 17 skipped。Windowsでは実ジャンクションを必須実行、Linuxでは実シンボリックリンクを実行。スキップはOS専用ケースとWindowsのシンボリックリンク権限によるもの。git diff --check成功。各操作の実行前後、復旧の再中断、チェックポイント保存、時刻設定、DB確定前後、登録直後の失敗を検証。旧計画は復元済みデータまたは検証可能な保存スナップショットの内容だけを巻き戻し対象にし、不明な作業データは保護する。DBスキーマとCLI成功JSONに変更なし。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
復元・ブランチ切り替えと復旧処理でリンク経由の書き込みを拒否し、ファイルとディレクトリの双方向構成変更に対応した。部分復元は選択外を変更しない。バージョン付き計画と固定サイズの進捗記録、再中断可能な巻き戻し、旧計画互換を追加した。Windows 201件・Linux 203件成功。READMEと構造化エラー説明を更新。
<!-- SECTION:FINAL_SUMMARY:END -->
