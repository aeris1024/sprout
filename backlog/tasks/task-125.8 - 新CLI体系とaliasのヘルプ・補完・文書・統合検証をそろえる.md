---
id: TASK-125.8
title: 新CLI体系とaliasのヘルプ・補完・文書・統合検証をそろえる
status: Done
assignee:
  - '@codex'
created_date: '2026-10-31 07:24'
updated_date: '2026-10-31 21:17'
labels:
  - cli
  - docs
  - usability
dependencies:
  - TASK-125.6
  - TASK-125.7
  - TASK-125.13
  - TASK-125.14
  - TASK-125.15
  - TASK-125.16
references:
  - README.md
  - gui/README.md
  - src/sprout/cli.py
  - tests/test_cli.py
  - tests/test_serve.py
  - scripts/create_sample_repo.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 132000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
親タスクの正規10入口と合意したaliasを、ヘルプ・シェル補完・README・利用例・テストで一貫して使える状態にする。
各CLI領域のタスクがその操作の回帰検証を持ち、このタスクでは全体の対応漏れ、利用導線、階層化されたコマンドとaliasの補完、外部連携経路の整合を確認する。既存33トップレベルとpreview下位操作から新構文への対応表を残す。
通常ヘルプは正規体系を中心とし、手打ちaliasの一覧と使い方に到達できる。Git名のaliasもSproutの挙動であること、trackにステージングがないこと、stash popがつぼみを消費することを明記する。
追補: go系・log系・message系・thumbnail系の配置変更と操作統合を区別し、最終の正規入口・alias・挙動差を説明する。重複するbranch switch/leaf restore/file history/leaf note/file coverは正規一覧へ戻さない。TASK-125.13でプレビューを葉全体の確認資料へ整理し、素材関連付けを廃止して表示名・説明・順序・置き換えを維持した結果を反映する。
確定したメディア方針も最終一覧へ反映する。代表プレビューの指定・バッジ・オプションを廃止し、表示順と置き換えを維持する（TASK-125.14）。「代表ファイル」は「サムネイル自動生成元」と表記する。素材関連付け廃止はTASK-125.13へ追跡し、旧代表指定が文書や補完・サンプルから再び案内されないことを検証する。
確定したラベル維持・プロジェクト全体一覧・GUI入力候補をTASK-125.15・TASK-125.16と整合させる。全ブランチの現存葉から候補を集計する範囲、既存候補の選択と新規入力の両立、葉ごとの一覧と全体一覧・履歴絞り込みの違いを文書化して検証する。
移行の最終整理も本タスクの担当とする。TASK-125.7によるGUI/スクリプトの正規構文移行後、段階的な動作維持のために残した仮の旧トップレベルや旧フラグ入口を整理し、正規体系と合意したaliasの最終公開契約をテストする。合意していない旧構文を恒久aliasとして増やさない。CLIの既存利用例やテストも正規/alias/移行用の区別を明確にする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 READMEのクイックスタート・全コマンド一覧・各機能例・JSON例とGUI READMEのCLI説明が新構文に整合し、旧33入口からの対応を確認できる
- [x] #2 rootと各下位操作のhelpが整合し、基本10入口・用途・必須引数・alias対応を迷わず確認できる
- [x] #3 PowerShell/bash/zshで階層化されたコマンドと対応aliasの補完、および葉・ブランチ・タグ参照の既存補完が機能することを検証する
- [x] #4 基本の保存から履歴閲覧・分岐・退避・復元・取り出し、添付管理、ゴミ箱、prune、保守まで、正規CLIの対応漏れがないことを統合検証する
- [x] #5 CLI・serve・alias・GUIの関連テストと必要なビルドが成功し、既存V1リポジトリとサンプルを正規構文で利用できる
- [x] #6 4系統の統合結果と確定したラベル維持を説明でき、TASK-125.13の素材関連付け廃止と表示名・説明・順序・置き換えの維持を含む実装・移行の完了を確認する
- [x] #7 ヘルプ・補完・GUI README・サンプル・アーカイブの案内が代表指定廃止・置き換え維持・サムネイル自動生成元への改称に整合し、TASK-125.14の実装と検証完了を確認する
- [x] #8 TASK-125.15・TASK-125.16のラベル一覧・候補表示と既存の付与/解除・履歴検索が検証され、CLI/GUIヘルプとREADMEが整合する
- [x] #9 ヘルプ・補完・GUI/README・JSON・アーカイブ・サンプルに廃止した素材関連付け操作の案内を残さず、葉全体の確認資料という位置付けと維持する表示名・説明・順序を説明する
- [x] #10 正規CLIへの利用箇所移行後に、段階的移行の仮の旧入口/旧フラグを整理し、最終公開入口と合意したaliasだけが案内・補完・実行契約として整合することを検証する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Remove temporary old command registrations/groups/flags, leaving canonical10 plus agreed aliases, and update generated archive/error guidance. 2. Migrate actual test argv and expected contracts to canonical commands or intentional aliases without test-only compatibility wrappers. 3. Align quickstart/reference/JSON examples, GUI README and sample guide with final syntax and old33-entry mapping, clarified go/labels/previews and flag-like values. 4. Exercise hierarchical completion protocol for PowerShell/bash/zsh; parse generated scripts in real pwsh/GitBash where available and record zsh interpreter limitation. 5. Run focused regression loops, final canonical/alias/serve/sample/V1 integration and whole backend+GUI/type/build checks; finalize after evidence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Final validation completed without repeating successful cases: original interrupted run covered463 cases (457 passed,3 skipped,3 outdated guidance assertions failed). Updated only those3 expected messages to canonical syntax; reran them plus315 unexecuted cases:301 passed,17 skipped in142.46s. Unique full-suite coverage:778 cases,758 passed,20 skipped,no outstanding failures. GUI262 tests,typecheck,Vite build passed; Rust9 tests passed in125.7 with unchanged Rust source. Completion35 tests cover PowerShell/bash/zsh protocols and real PowerShell/Git Bash script parsing; zsh interpreter is not installed,so interactive zsh was not tested. Independent real CLI V1 workflow and exact final command allowlist passed; JSON examples and10/15/33 documentation mappings validated. Preserved original CRLF in repository tests; diff check passes with cr-at-eol.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed canonical CLI migration: removed temporary old routes/flags, retained only10 canonical entries plus agreed aliases, aligned help/completion/docs/JSON/sample/archive guidance and migrated actual regression argv. Verified778 backend cases (758 passed,20 skipped) across interrupted/resumed runs,262 GUI tests,typecheck/build,9 Rust tests,completion protocols and real CLI integration. V1 unchanged; interactive zsh not available.
<!-- SECTION:FINAL_SUMMARY:END -->
