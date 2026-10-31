---
id: TASK-124
title: GUIの通知に出るCLIの英語エラーを用語表の言葉で表示する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-31 06:05'
updated_date: '2026-10-31 06:24'
labels:
  - gui usability
dependencies: []
references:
  - src/sprout/repository.py
  - gui/src/lib/sprout.ts
  - gui/README.md
priority: low
type: enhancement
ordinal: 123000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUIの通知には、CLIが返す英語のエラー文（`unknown commit: ...`、`nothing to commit`、`commit message cannot be empty` など）がそのまま表示され、TASK-109で統一した画面の用語と食い違っている。CLIの文言を保ったまま、GUIから到達できる主なエラーを利用者に分かる日本語で表示する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GUIから到達できる主なエラーが`gui/README.md`の用語表の言葉（葉、メッセージ、ブランチ、つぼみなど）で通知に表示される
- [x] #2 GUIに対応付けのないエラーは、CLIが返した原文のまま表示される
- [x] #3 CLIの`message`の文言と終了コードは変わらず、`--json`のエラーで主なエラーを`code`で識別できる
- [x] #4 `gui/README.md`の「用語」の節が実際の対象範囲を説明している
- [x] #5 `gui`の`pnpm test`と`pnpm build`、リポジトリのルートのCLIテストが成功する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. CLIのmessageは変えず、GUIから到達できるSproutErrorへcodeとdetailsを付ける（CLIの利用者とテストはmessageに依存し、GUIは既にcodeで分岐している）。
2. gui/src/lib/cliErrors.ts にcodeから日本語への対応表を置き、normalizeCliErrorで適用する。対応のないcodeと旧CLIのsprout_errorは原文のまま。
3. 対応表のcodeがCLIのソースに存在することと、旧用語が混ざらないことをvitestで検査する。
4. isUninitializedProjectをcode判定へ移し、旧CLI向けにmessage判定も残す。ComparePanelの生のcode表示を外す。
5. gui/README.mdの用語の節とルートREADMEのエラーコードの説明を更新し、テストとビルドを確認する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
CLIのmessageを変えずcodeを付ける案を採用した。CLIの利用者とテストがmessageに依存し、GUIは既にcodeで分岐しているため。not_initializedへの変更で旧来のsprout_errorを期待していたtest_cliとtest_serveの2件を更新した。normalizeCliErrorは同じエラーに複数回通るため、translatedで再翻訳を防いでいる。対象外: 内部の不整合を示すエラー、move・archive・pruneなどGUIから呼ばないコマンドのエラーは原文のまま。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GUIから到達できる主なSproutErrorにcodeとdetailsを付け、gui/src/lib/cliErrors.tsで用語表の言葉へ対応付けた。未対応のcodeは原文のまま表示する。pytest 613 passed / 20 skipped、pnpm test 229 passed、pnpm build成功で確認した。実際のTauriウィンドウでの表示は未確認で、通知の表示はvitestで確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
