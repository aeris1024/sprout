---
id: TASK-28
title: コミットに後付けのメモとラベルを付けられるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:39'
updated_date: '2026-08-08 18:08'
labels: []
dependencies:
  - TASK-37
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: medium
type: feature
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

コミットメッセージは作成時に固定されるため、「提出した版」「ボツ」「クライアントOK」のような後から分かる情報を記録する場所がない。編集可能なメモとラベルがあると、GUIのツリービューでの絞り込み・色分け、CLI検索、静的アーカイブでの整理に利用できる。タグは不変の目印、メモとラベルは編集可能な注記として役割を分ける。

## 前提となる保存形式

TASK-37のSchema Version 3で用意されるcommit_notesとcommit_labelsを使用する。commit_notesはコミットごとに1件のnoteとupdated_atを持ち、commit_labelsはコミットごとに複数の重複しない自由文字列ラベルを持つ。

## 機能範囲

- コミットのメモを設定、上書き、削除できる
- コミットへラベルを追加、削除できる
- 空または空白だけのラベルは拒否する
- show、log、JSON出力でメモとラベルを確認できる
- logをラベルで絞り込める
- TASK-22のコミットグラフにメモとラベルを含め、GUIと静的アーカイブから利用できる
- 書き込み操作は他のリポジトリ更新と同様に排他制御する
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 メモを設定・上書き・削除でき、変更時に更新日時が更新される
- [x] #2 メモは前後の空白を除去し、空文字は削除として扱い、20,000文字超を拒否する
- [x] #3 ラベルはUnicode NFC正規化と前後空白除去を行い、1〜64文字、コミットあたり最大32件、大文字小文字を区別する
- [x] #4 複数ラベルを追加・削除でき、同一ラベルを重複させない
- [x] #5 showとlogの人間向け表示およびJSON出力でメモ、メモ更新日時、ラベルを確認できる
- [x] #6 logを正規化後の完全一致ラベルで絞り込める
- [x] #7 メモとラベルの書き込み操作をリポジトリロックで排他制御する
- [x] #8 TASK-22から再利用できるRepository APIでコミット注記を取得できる
- [x] #9 READMEと自動テストが設定、変更、削除、制約、検索、出力を検証する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 注記モデル・入力正規化・制約をRepositoryへ追加する。 2. ロック付きメモ／ラベル更新と一括取得APIを実装する。 3. logのラベル絞り込みとshow/logの注記出力を追加する。 4. note/label CLIを実装する。 5. READMEとテストを更新し、全テストを実行する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
RepositoryにCommitAnnotations、一括取得、ロック付きメモ／ラベル更新、正規化・上限制約、ラベル完全一致logフィルターを追加した。CLIにnote/labelコマンドを追加し、show/logの通常表示とJSONへ注記を統合した。検証: uv run pytest --basetemp .test-tmp-task28b -p no:cacheprovider -q（119 passed, 2 skipped）。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
コミットへ後付けできるメモとラベル、ラベル履歴検索、show/log注記出力を実装した。正規化・件数／文字数制約・排他制御・一括取得APIを含み、README更新と全119テスト成功で検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
