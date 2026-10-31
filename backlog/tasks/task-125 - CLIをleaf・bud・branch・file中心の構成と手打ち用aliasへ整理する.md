---
id: TASK-125
title: CLIをleaf・bud・branch・file中心の構成と手打ち用aliasへ整理する
status: To Do
assignee: []
created_date: '2026-10-31 07:21'
updated_date: '2026-10-31 07:35'
labels:
  - cli
  - usability
dependencies: []
references:
  - src/sprout/cli.py
  - src/sprout/serve.py
  - gui/src/App.tsx
  - README.md
  - gui/README.md
priority: medium
type: enhancement
ordinal: 124000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CLIをleaf・bud・branch・file中心の正規体系と手打ちaliasへ整理する親タスク。ユーザーの追加依頼により、名前・配置の変更に加えてgo系・log系・message系・thumbnail系の操作入口を統合する。プレビューとLabelの機能採否・統合・削減・CLI配置は未決定としてTASK-125.13でユーザーと確認する。実装への着手は今回の依頼に含まれない。

正規トップレベルは init / status / go / leaf / bud / branch / file / trash / maintenance / serve の10入口。通常ヘルプは正規体系を中心とし、alias対応も別途確認できる。GUIは確定した正規体系を使う。

決定済みの正規構成:
- leaf create -m TEXT / list [PATH]（素材ID履歴も--file-idで同じ入口へ統合）/ tree / show LEAF / edit LEAF（メッセージ・メモの編集）/ delete LEAF / prune START_TAG END_TAG または --all / archive --output DIR
- leaf tag list / create NAME [LEAF] / comment NAME TEXT / delete NAME
- leaf thumbnailは個別のshow/set/delete/exportと、プロジェクト単位の自動生成元の確認・指定・解除・既存葉への適用をまとめる。生成元の下位構文は実装前に整える。
- bud save [--name NAME] [--keep-files] / list / restore BUD / rename BUD NAME / delete BUD
- branch list [--deleted] / create NAME [LEAF] / rename OLD NEW / comment NAME TEXT / delete NAME
- file track PATH... / untrack PATH... / list / move OLD NEW / diff [LEAF_A] [LEAF_B] / restore LEAF PATH... / export LEAF [PATH...] --output DIR / cat LEAF PATH
- trash list / show ID / restore ID / purge ID、maintenance stats / doctor / gc
- init [PATH]、status [PATH...]、go TARGET、serveはトップレベル。

4系統の統合:
1. TASK-125.9: go/switch/全体restoreの移動をgoへ集約し、部分復元はfile restoreへ。branch switchとleaf restoreを別の正規入口として追加しない。既定で未保存変更をつぼみに退避する。従来の拒否・discard・ブランチを保つ全体復元の扱い、明示ブランチ・空ブランチ等の差分は実装前に確認する。
2. TASK-125.10: logとfile-historyをleaf listへ統合し、file historyを別の正規入口として追加しない。パスと素材IDの検索範囲・抽出条件の違いを明示して保持する。
3. TASK-125.11: messageとnoteをleaf editへ統合し、メモの閲覧はleaf show。leaf noteの独立した正規入口は作らない。Labelの取り込みや削減は未決定。
4. TASK-125.12: thumbnailとcoverをleaf thumbnailへ統合し、file coverを別の正規入口として追加しない。サムネイルと代表プレビューを混同しない。

手打ちalias（Sproutの正規処理への別名）:
commit -m TEXT -> leaf create -m TEXT
log [PATH] / --file-id FILE_ID -> leaf listの同じ検索
show LEAF -> leaf show LEAF
tree -> leaf tree
diff ... -> file diff ...
track PATH... -> file track PATH...
untrack PATH... -> file untrack PATH...
mv OLD NEW -> file move OLD NEW
switch NAME -> goの明示的なブランチ指定（TASK-125.9で確定）
stash push/list/pop BUD/drop BUD -> bud save/list/restore BUD/delete BUD
tag -> leaf tag list
tag NAME [LEAF] -> leaf tag create NAME [LEAF]

範囲と保留:
- pruneを高度な履歴整理として残す。既存オプションや安全確認、バイナリ標準出力、必要なJSON契約を維持する。統合で動作差の整理が必要な部分は黙って同一扱いせず、対応タスクで確認・検証する。
- previewとLabelについては旧案のleaf preview / leaf labelや代表指定・素材関連付けを確定扱いしない。TASK-125.13でユーザーと決定するまでは現行機能・保存データ・既存呼び出しを保持し、削減や統合を実装しない。確定後に必要な実装タスクと依存関係を追補する。
- 保存形式は現行V1のまま。CLI統合自体でschema変更、データ移行、保存形式の旧版互換処理を追加しない。
- aliasはGitのステージングやstash applyを追加するものではない。全旧構文の恒久互換維持を要件にはしないが、段階的な移行中は既存GUIが利用できる状態を維持する。
- GUIの新機能追加や画面の再設計は対象外。確定した正規構文への呼び出し移行、ヘルプ・補完・文書・統合検証を扱う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 4系統の操作統合を含む正規10入口に現行機能の扱いが対応し、独立したbranch switch・leaf restore・file history・leaf note・file coverを重複した正規入口として追加しない
- [ ] #2 指定aliasが統合後の正規処理を呼び出し、引数・結果・JSON・終了コード・安全確認が対応先と一致する
- [ ] #3 V1保存形式とpruneを維持し、go等の動作差がある部分は統合前に方針確認・検証を行う。preview/Labelはユーザーの判断前に機能・データを変更しない
- [ ] #4 GUI・serve・スクリプト・ヘルプ・補完・文書を確定した正規体系へそろえ、未決定のpreview/Labelの扱いは検討タスクと決定後の実装へ追跡できる
<!-- AC:END -->
