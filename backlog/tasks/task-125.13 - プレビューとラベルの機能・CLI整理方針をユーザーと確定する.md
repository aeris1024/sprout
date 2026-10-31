---
id: TASK-125.13
title: プレビューを葉全体の確認資料へ整理し素材関連付けを廃止する
status: To Do
assignee: []
created_date: '2026-10-31 07:33'
updated_date: '2026-10-31 09:07'
labels:
  - cli
  - gui
  - usability
dependencies:
  - TASK-125.1
  - TASK-125.14
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - src/sprout/archive.py
  - src/sprout/trash.py
  - gui/src/components/PreviewPanel.tsx
  - gui/src/App.tsx
  - tests/test_preview_metadata.py
  - tests/test_previews.py
  - scripts/create_sample_repo.py
  - README.md
  - gui/README.md
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 137000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ユーザーが確定したプレビュー方針を実装する。プレビューは個別素材ではなく葉全体の確認資料として扱い、同じ葉の保存ファイルを対象素材として選ぶ関連付けを廃止する。表示名・説明・表示順は維持し、追加・表示・取り出し・削除・置き換えを利用できるようにする。
正規CLIは既に合意したleaf preview配下のlist/add/replace/delete/export/order/edit/imageへ整理する。editは表示名・説明を編集する。素材関連付けの入力・解除オプションやGUIの対象素材選択・対象素材表示、プレビューのfile_idsと関連情報に依存するJSON・アーカイブ・復旧処理・サンプル・文書を整理する。代表指定の廃止はTASK-125.14が担当し、このタスクで再導入しない。

維持する動作:
- プレビューは追跡対象外のファイルも添付でき、追跡ファイルとの関連を必須にしない。
- 表示名・説明は従来の制約と正規化を維持し、表示名未設定時は元のファイル名を表示する。
- 表示順は保存され、重要なものは上へ移動できる。
- 置き換えは同じ一覧項目の内容修正として残し、添付ID・位置・最初の登録日時・表示名・説明を維持する。
- 置き換え前の内容や削除した添付はゴミ箱から復旧できる。復旧時に廃止した代表指定や素材関連付けを機能として復活させない。

素材関連付けの保存情報・JSON・既存の復旧記録の扱いを整合させる際も、プレビュー原本・表示名・説明・順序を失わない。追跡ファイルそのものの不変素材ID、改名・移動をまたぐファイル履歴、サムネイル自動生成元の指定は別機能として維持する。V1方針と整合させ、保存形式のバージョン引き上げや旧版互換機構を追加することをこのタスク登録で決定しない。
ラベル維持と一覧・GUI候補はTASK-125.15/125.16、サムネイル自動生成元はTASK-125.12へ委ねる。仕様の採否待ちだった本タスクを実装タスクへ更新したが、今回の依頼はBacklog反映のみ。実装は未着手。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 プレビューを葉全体の添付資料として扱い、GUIの対象素材選択・表示、CLIの関連付け指定/解除、プレビューのJSONやアーカイブから素材関連付けの機能を廃止する
- [ ] #2 leaf previewのlist/add/replace/delete/export/order/edit/imageを利用でき、editで表示名・説明を編集できる。代表指定や素材関連付けの操作を増設しない
- [ ] #3 表示名・説明の値・既存制約・正規化と表示名未設定時の元ファイル名表示を維持し、順序の変更と再起動後の維持を利用できる
- [ ] #4 追跡対象外ファイルの添付と置き換えを維持し、置き換えでは添付ID・位置・最初の登録日時・表示名・説明を保ち、失敗時に元の添付を変更しない
- [ ] #5 削除・置き換えのゴミ箱復旧で原本と表示用メタ情報・順序を保ち、既存の関連付けを含む復旧記録を扱っても素材関連付けや代表指定を機能として復活させない
- [ ] #6 ファイル自身の不変素材ID・改名移動をまたぐ履歴・サムネイル自動生成元の指定・ラベルは変更せず、V1方針と整合する
- [ ] #7 CLI・GUI・serve・JSON・アーカイブ・サンプル・文書と関連テストを更新し、素材関連付け廃止、表示名/説明/順序・置き換え/復旧の維持を検証する
<!-- AC:END -->
