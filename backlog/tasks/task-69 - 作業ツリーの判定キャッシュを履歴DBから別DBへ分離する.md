---
id: TASK-69
title: 作業ツリーの判定キャッシュを履歴DBから別DBへ分離する
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
  - tests/test_v1_storage.py
  - tests/test_repository.py
  - README.md
priority: high
type: enhancement
ordinal: 69000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

TASK-67で用意したworktree_cacheは履歴DBの必須構造として検証され、キャッシュ表の欠落や追跡対象外のパスを参照する不正なキャッシュ行によって、履歴を開けず再初期化を要求される。再生成できる補助情報の異常が、保存済みの履歴へアクセスできない原因になっている。

## ゴール

V1の初期保存構造として、作業ツリーの判定キャッシュを履歴DBから別の再生成可能なDBへ分離する。履歴DBからworktree_cacheとそれへの依存を外し、キャッシュの形式や寿命を履歴の必須構造から独立させる。

キャッシュが欠落・破損・非対応形式・書き込み不可でも履歴の読み出しや通常操作を妨げず、履歴DBの再初期化を要求しない。必要時にキャッシュを再生成し、利用できなければ通常のハッシュ計算へ戻れるようにする。追跡解除・移動・復元などで古い記録を無効化する方針は維持する。

## 対象範囲

別DBとしての保存基盤と異常時の扱い、既存の無効化処理、履歴DBの構造検証、テスト、README更新を含める。Schema Versionは1を維持し、開発用の旧キャッシュは移行しない。履歴DBの検証と非変更拒否の方針は維持する。

キャッシュを使ったハッシュ計算の省略は後続のTASK-56で実装する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 新規V1の履歴DBからworktree_cacheとそれへの依存を外し、再生成可能な別DBで判定キャッシュを管理する基盤がある
- [x] #2 キャッシュの欠落・破損・非対応形式・書き込み不可が履歴の読み出しや通常操作を妨げず、履歴DBの再初期化を要求しない
- [x] #3 必要時にキャッシュを再生成でき、利用できない場合は通常のハッシュ計算へ安全に戻れる
- [x] #4 追跡解除・移動・全体および部分復元などで古いキャッシュ記録を無効化する方針が別DBへの分離後も維持される
- [x] #5 異常なキャッシュによって保存済みの履歴・参照・作業ファイルが意図せず変更されないことを自動テストで検証する
- [x] #6 履歴DBと別DBの役割、キャッシュの再生成とフォールバックをREADMEへ記載し、キャッシュ異常時と既存操作のテストを追加する
- [x] #7 Schema Versionは1を維持し、開発用の旧キャッシュを移行せず、ハッシュ計算を省略する判定ロジックはTASK-56に残す
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 任意の判定キャッシュを専用DBへ分離し、破損・非対応・書込み不可時はキャッシュを無効化する。2. 追跡解除・移動・復元・欠落ファイル確定時の無効化を接続する。3. 異常系と既存操作をテストしREADMEを更新する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
worktree-cache.dbを遅延生成し、独立したuser_versionと構造を検証するWorktreeCacheを追加。欠落・破損・形式不一致は再生成、権限不足・ロック・危険なパスは利用を見送る。履歴DB更新に紐づけて全記録を保守的に失効させ、無効化が失敗しても再オープン時に古い記録を再利用しない。履歴DBから表とFK依存を除去し、旧キャッシュ表は変更・移行せず無視する。README更新。全Pythonテスト335成功・19スキップ（環境依存）。欠落・破損・バージョン・列/表欠損・書込不可・ロック・旧キャッシュ・非変更・既存の追跡/移動/復元を検証。Schema Version 1維持、ハッシュ省略はTASK-56に残した。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
判定キャッシュを履歴DBから独立した任意DBへ分離。異常時の再生成・通常ハッシュへの復帰と既存操作の無効化を実装し、全Python335テスト成功で検証。
<!-- SECTION:FINAL_SUMMARY:END -->
