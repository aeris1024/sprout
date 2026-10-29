---
id: TASK-56
title: 未保存変更の判定でファイル全体のハッシュ計算を省略して高速化する
status: Done
assignee:
  - '@claude'
created_date: 2026-10-27 15:03
updated_date: '2026-10-29T14:08:00Z'
labels:
  - cli
  - performance
dependencies:
  - TASK-69
references:
  - src/sprout/repository.py
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: medium
type: enhancement
ordinal: 56000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

TASK-51の計測では、追跡ファイル20件・計40 MBの作業ツリーでrestoreに約1.2秒、statusに約0.4秒かかった。未保存の変更の判定で、変更のないファイルも毎回全体をハッシュ計算していることが主な原因である。GUI刷新後は移動のたびに判定が走るため、応答速度に直接影響する。

## ゴール

前回ハッシュ計算したときのサイズ・更新日時などを記録し、変わっていないファイルのハッシュ計算を省略する。内容が変わったのに検出できない状態を作らないことを最優先とする。

## キャッシュの保存先と前提

TASK-69で履歴DBから分離する、再生成可能な別のキャッシュDBを利用する。キャッシュの欠落・破損・非対応形式・書き込み不可によって履歴の読み出しや通常操作を妨げず、利用できない場合は全体のハッシュ計算へ安全に戻る。履歴DBの再初期化を要求しない。

本タスクでは、この別DBの記録を利用する安全な判定の省略と性能改善を実装する。キャッシュを履歴DBの必須構造として追加しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 サイズ・更新日時などが前回の計算時と一致する追跡ファイルは、未保存変更の判定でハッシュを再計算しない
- [x] #2 内容が変更されたファイルは、更新日時の粒度や同一秒内の書き換えを含めて変更として検出される
- [x] #3 記録が欠落・破損・不一致の場合は全体のハッシュ計算へ安全に戻る
- [x] #4 TASK-51と同じ条件で、変更のない作業ツリーに対するstatusとrestoreの所要時間の改善が計測・記録される
- [x] #5 変更検出の境界条件と記録の破損時の動作がテストされる
- [x] #6 status、restore、switch、go、commitの結果が高速化前と一致する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. WorktreeCacheに複数パスを1接続で読み書きするlookup/recordを追加する。
2. Repositoryに_hash_worktree_filesを追加し、サイズ・mtime・ctime・ファイルID（st_dev:st_ino）が一致し、記録時点でmtimeが2秒以上前（RACY_MARGIN_NS）の記録だけハッシュを再利用する。それ以外は読み直し、読み取り前後で属性が変わらなかったときだけ記録する。
3. status、diff（作業ツリー）、_has_unsaved_changes、pruneの作業ツリー照合、復元計画のバックアップ用ハッシュをこのヘルパーへ置き換える。_materializeのキャッシュ失効は計画作成の後（ファイル書き換え前）へ移す。
4. 退避直前の安全確認（_matches_restore_file）とcommit・つぼみ保存は内容を読み直したままにする。
5. 境界条件と破損時の動作をテストし、TASK-51と同じ条件でmainと比較計測する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
既存の`sprout move`（追跡ファイルの移動）と名前が重なるため、スナップショット間を移動する新コマンドの名前をgoに決定した（2026-10-28 ユーザー決定）。

計測（2026-10-29、Windows 11、追跡ファイル20件・各2 MB、コミット30件、in-process中央値15回、hash_fileの所要時間を内訳として計測）:
- status（変更なし）: main 145 ms（ハッシュ127 ms） → 本変更 21 ms（ハッシュ0 ms）。別の回ではmain 174〜283 ms → 34〜46 ms。
- restore（直前にstatusあり）: ハッシュ 400 ms → 170 ms。go（直前にstatusあり）: ハッシュ 525 ms → 167 ms。restore（直前のstatusなし）: ハッシュ 580 ms → 453 ms。
- restore・goの合計時間は1.4〜1.9秒で、20ファイルすべてをfsync付きで書き直す処理が大半を占め、計測ごとのばらつきがハッシュ削減分より大きかった。CLIのプロセス起動はこの環境で600〜700 msあり、CLI単位の計測はノイズが大きかったため内訳で記録した。
判断:
- racy判定はmtimeだけに適用し、ctimeは一致比較のみとした。Windowsのctimeは作成日時で書き換えでは変わらず、racy判定に含めると復元直後のファイルが常に再計算になるため。
- サイズとmtimeを元の値に戻す書き換えは、ctime・ファイルIDが変わらない環境では検出できない（Gitと同じ制約）。READMEに明記した。
- 退避直前の安全確認は計画作成から実行までの変更を検出する保護なので、キャッシュを使わず内容を読み直す。
残課題の候補（未作成）: 復元で内容が同じファイルの書き直しを省く、復元・go後に書き込んだファイルの記録を残して直後のstatusを速くする。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
未保存変更の判定で、変更のないファイルのハッシュ計算を作業ツリーキャッシュ（worktree-cache.db）で省略した。サイズ・mtime・ctime・ファイルIDが一致し、記録時点でmtimeが2秒以上前の記録だけを再利用する。同じ時刻粒度内の書き換え、読み取り中の変更、キャッシュの破損・欠落・不一致では内容を読み直す。status・diff・restore・switch・go・bud --restore・pruneが対象で、commit・つぼみ保存と退避直前の安全確認は従来どおり内容を読む。
検証: 新規テスト13件（tests/test_worktree_hash_cache.py）を含め、pytestは348 passed / 19 skipped。TASK-51と同条件の計測で、statusは145 ms → 21 ms、restore・goのハッシュ時間は400〜525 ms → 約170 msになった。restore全体はファイルの書き直しが支配的で、改善は誤差の範囲にとどまる。
リスク: サイズと更新日時を元の値に戻す書き換えは、ctime・ファイルIDが変わらない環境では検出できない（Gitと同じ。READMEに記載）。
<!-- SECTION:FINAL_SUMMARY:END -->
