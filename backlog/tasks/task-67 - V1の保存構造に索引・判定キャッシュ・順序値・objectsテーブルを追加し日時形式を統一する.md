---
id: TASK-67
title: V1の保存構造に索引・判定キャッシュ・順序値・objectsテーブルを追加し日時形式を統一する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-28 19:16'
updated_date: '2026-10-28 19:35'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - gui/src/lib/sprout.ts
  - tests/test_v1_storage.py
  - README.md
priority: high
type: enhancement
ordinal: 67000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

Sproutはまだ実利用されていない。check_schemaはsqlite_masterのSQLを完全一致で検証するため、正式リリース後は索引1つ・列1つの追加でもSchema Versionの更新と移行処理が必要になる。TASK-62でV1の初期仕様を見直した後のレビューで、後から追加すると移行が必要になる不足点と、今のうちに確定すべき保存仕様が見つかった。Schema Version 1のまま、V1の初期仕様へ取り込む。

## ゴール

### 索引の補完
commit_files(object_hash)に索引がなく、commitのたびに同一内容の最小mtimeを求める処理と、部分的なsaved snapshot判定が全件走査になっている。履歴量に比例して保存が遅くならないよう、内容ハッシュによる検索と、commits.branch_id・tags.commit_id・branches.commit_idなど外部キーの子側の検索・削除検査に必要な索引を揃える。

### 作業ツリーの判定キャッシュの保存場所
TASK-56（未保存変更判定の高速化）では、追跡ファイルごとに前回ハッシュ計算時のサイズ・更新日時などと内容ハッシュを記録する必要がある。判定ロジックはTASK-56で実装するが、その記録を保存できるV1の必須構造を先に用意し、TASK-56でSchema Versionを上げずに済むようにする。

### 安定した並び順
コミットとつぼみは秒精度のcreated_atとrowidで並べているが、明示的なINTEGER PRIMARY KEYを持たない表のrowidはVACUUMで振り直され得る。作成順を表す明示的で単調増加する順序値を持たせ、並び順をrowidに依存させない。

### 日時形式の統一
commits・tags・budsの日時は秒精度、notes・attachments・repository_created_atはマイクロ秒精度で、形式が混在している。保存する全日時のUTC表現と精度を1つに統一する。

### objectsテーブルと内容ごとの更新日時
commit_files.mtime_nsは実ファイルの更新日時ではなく「その内容を最初に保存したときの更新日時」を内容ごとの正規値として扱っており、内容単位の属性をコミット×パスの行へ重複保存している。保存済みオブジェクトをDBで管理するobjectsテーブル（内容ハッシュ、元サイズ、保存サイズ、保存形式・圧縮方式、作成日時、内容ごとの正規更新日時など）を導入し、正規更新日時をobjectsへ移す。commit_files・commit_attachments・bud_filesのobject_hashはobjectsを外部キーで参照する。

オブジェクトごとに保存形式を記録することで、将来、既に圧縮済みの形式を無圧縮で保存する、大きなファイルを分割保存するなどの変更をSchema Versionの更新なしに追加できる余地を作る。本タスクでは既存の保存形式（zstd）を維持し、保存形式の切り替え自体は実装しない。

## 対象範囲

保存構造と既存操作の対応、doctor・gc・stats・pruneのobjectsとの整合、CLI・JSON・GUIの型で必要な範囲、テスト、README更新を含める。TASK-56の判定ロジック、保存形式・圧縮方式の切り替え、分割保存、既存データの移行処理は含めない。変更前の開発用DBは自動変換・修復せず、変更せずに拒否して再初期化を案内する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 新規リポジトリがSchema Version 1のまま、追加の索引・判定キャッシュ用構造・明示的な順序値・objectsテーブルを持つ初期仕様で作成され、check_schemaがこれらを必須構造として検証する
- [x] #2 内容ハッシュによる検索（commit時の正規更新日時の取得、部分的なsaved snapshot判定）と外部キーの子側の検索が索引を使い、コミット数に比例した全件走査にならないことがクエリプランのテストで確認される
- [x] #3 追跡ファイルごとに前回の判定時のサイズ・更新日時などと内容ハッシュを記録できる構造があり、追跡解除・移動・全体restore時に古い記録が残らない。記録を使った判定の省略はTASK-56で扱う
- [x] #4 コミットとつぼみの一覧・log・tree・pruneの並び順が明示的な順序値で決まり、同一秒内の作成やVACUUM後も作成順が保たれる
- [x] #5 保存したすべてのオブジェクトがobjectsテーブルに内容ハッシュ・元サイズ・保存サイズ・保存形式・作成日時・正規更新日時とともに記録され、commit_files・commit_attachments・bud_filesのobject_hashが外部キーで参照する
- [x] #6 同一内容の正規更新日時がobjectsで1か所に管理され、commit・restore・export・つぼみ復元で復元されるファイルの更新日時が変更前と同じ規則で決まる
- [x] #7 オブジェクトファイルの書き込みとobjectsへの登録が失敗・中断しても参照切れが残らず、未登録のオブジェクトファイルはgcで回収される。doctorはobjectsとファイルの欠落・破損・サイズ不一致を検出する
- [x] #8 stats・gc・pruneがobjectsテーブルと整合して動作し、参照中のオブジェクトとそのobjects行を削除しない
- [x] #9 既存の操作（track・commit・restore・switch・go・つぼみ・thumbnail・メモ・ラベル・タグ・export・cat・doctor・stats・gc・prune）とCLI・JSON・GUIの互換性が維持される
- [x] #10 変更前のV1や必須構造が欠けたDBを、データを変更せずに拒否して再初期化を案内し、既存データの移行処理は追加しない
- [x] #11 索引の利用、順序値、日時形式、objectsの外部キーと失敗時の整合、判定キャッシュの構造と後片付け、変更前V1の非変更拒否が自動テストで検証され、READMEにV1の初期仕様の更新が記載される
- [x] #12 commits・tags・buds・commit_notes・commit_attachments・objectsの日時とrepository_created_atが、統一したUTC表現と精度で保存され、CLI・JSON出力とGUIの表示が新しい形式で正しく動作する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. objectsテーブル（hash・size・stored_size・encoding・file_mtime_ns・created_at、UNIQUE(hash,size)）を追加し、commit_files・commit_attachments・bud_filesから(object_hash,size)の複合外部キーで参照する。commit_files.mtime_nsは削除し、内容ごとの正規更新日時をobjects.file_mtime_nsへ移す（初回にファイルとしてコミットされたときに設定し、以後変えない）。bud_files.mtime_nsは作業ファイルの実時刻なので維持する。
2. オブジェクト書き込み後、同じDBトランザクション内でobjectsへ登録してから参照行を挿入する（commit・thumbnail・つぼみ）。書き込み後の失敗で残る未登録ファイルはgcで回収し、doctorで報告する。
3. 外部キーの子側とobject参照に索引を追加し、saved snapshot判定（完全・部分）を(object_hash,size)索引で候補を絞る方式に変更する。EXPLAIN QUERY PLANと全外部キーの索引被覆をテストする。
4. tracked_pathsを外部キーで参照するworktree_cache（size・mtime_ns・ctime_ns・file_id・object_hash・recorded_ns）を追加する。追跡解除と全体restoreはCASCADE、移動と部分restoreは明示的に削除する。書き込みロジックはTASK-56で実装する。
5. commitsとbudsに単調増加のseqを追加し、graph・buds・prune・treeの並び順をseqで決める。
6. 保存する全日時をマイクロ秒精度のUTC ISO 8601（+00:00）に統一し、スキーマのCHECKとcheck_schemaで形式を検証する。
7. doctor・gc・stats・pruneをobjectsと整合させる。check_schemaの必須テーブルを更新し、変更前V1の非変更拒否を維持する。
8. 既存テストを新構造へ更新し、新規テストを追加。README更新、Python全テスト・GUIテスト/ビルド・別プロセスCLI/JSONで検証する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 実装

- objectsテーブル（hash・size・stored_size・encoding・file_mtime_ns・created_at、UNIQUE(hash,size)）を追加し、commit_files・commit_attachments・bud_filesから(object_hash,size)の複合外部キーで参照する。オブジェクトのファイル書き込み後、参照行と同じトランザクションで登録する。
- commit_files.mtime_nsを削除し、内容ごとの正規更新日時をobjects.file_mtime_nsへ移した。初めてファイルとしてコミットされたときに設定し、以後変えない（thumbnailやつぼみだけの内容はNULL）。従来のMIN(commit_files.mtime_ns)はprune後に変わり得たが、objects行がある限り固定される。bud_files.mtime_nsは作業ファイルの実時刻として維持した。
- 外部キーの子側すべてに索引を追加した（repository_stateは1行限定のため除外）。saved snapshot判定は完全・部分とも(object_hash,size)索引で候補コミットを絞る方式にし、GROUP BYによるcommit_filesの全件走査をなくした。
- worktree_cache（size・mtime_ns・ctime_ns・file_id・object_hash・recorded_ns）をtracked_pathsへのON DELETE CASCADEで追加した。追跡解除・全体restore・消えたファイルのコミットはCASCADEで、移動と部分restoreは明示的に削除する。書き込みはTASK-56の範囲。
- commitsとbudsにUNIQUEな連番seqを追加し、tree・つぼみ一覧・prune・CLI treeの並び順をseqで決める。
- 保存する全日時をutc_timestamp()（マイクロ秒精度・+00:00）に統一し、各列のGLOB CHECKとcheck_schemaで検証する。
- doctorはobjects行ごとに欠落・破損・サイズ不一致・非対応encodingを、加えて未登録ファイル・objects行のない参照・ファイル時刻のない内容を報告する。gcは未参照のobjects行を削除してからファイルを消す。statsのobjects件数・容量はobjectsテーブルから、pruneの回収容量はstored_sizeから求める。
- GUIのコードは変更していない（JSONの日時は文字列のまま精度だけ変わる）。

## 検証

- Python全体: .venv/Scripts/python.exe -m pytest -q -rs -p no:cacheprovider --basetemp .test-tmp/t67-final tests は315 passed, 19 skipped。スキップはWindowsのsymlink作成権限18件と非Windows向け大小文字判定1件。
- 追加テスト: 全外部キーの索引被覆、SAVED_FILE_COMMITS_SQLのEXPLAIN QUERY PLAN、objectsの記録と正規更新日時、thumbnail由来の内容の初回コミット時刻、DB制約8種、登録中断時の未参照とgc回収、gcとstatsの整合、doctorの4種の検出、worktree_cacheの後片付け、時計の巻き戻りとVACUUM後の並び順、pruneの作成順、全日時の形式、repository_created_atの形式、不完全なV1の非変更拒否4種。
- GUI: vitest runは51 passed、tsc --noEmit成功。
- 別プロセスのCLI/JSONでinit・track・thumbnail付きcommit・note・tag・bud・go・tree・show・export・doctor・stats・gc/prune dry-runを確認。HEADのコードで作成した変更前V1を新CLIがDB本体を変更せず拒否することも確認した。
- git diff --check成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
V1の初期仕様に、objectsテーブル（内容ごとの正規更新日時と保存形式を保持し、複合外部キーで参照）、外部キーとobject参照の索引、worktree_cache、コミットとつぼみの連番seq、マイクロ秒精度UTCへの日時統一を追加した。doctor・gc・stats・pruneをobjectsと整合させ、変更前V1は変更せず拒否する。Python全体315件成功・環境条件19件スキップ、GUI 51件成功とtsc、別プロセスCLI/JSON、旧コードで作ったV1の非変更拒否、差分チェックで確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
