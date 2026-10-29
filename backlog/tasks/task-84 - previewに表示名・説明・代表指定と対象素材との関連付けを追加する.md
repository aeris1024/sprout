---
id: TASK-84
title: previewに表示名・説明・代表指定と対象素材との関連付けを追加する
status: To Do
assignee: []
created_date: '2026-10-29T20:09:00Z'
labels: []
dependencies:
  - TASK-83
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - src/sprout/archive.py
  - gui/src/components/PreviewPanel.tsx
  - gui/src/components/CommitPanel.tsx
  - tests/test_previews.py
  - gui/README.md
priority: medium
type: feature
ordinal: 83000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在のpreviewはコミット全体への添付で、元ファイル名・形式・表示順だけでは、どの素材のどの確認用ファイルなのかが分かりにくい。画像・音声・モデル等の複数添付を整理できるよう、原本のファイル名とは別の表示名と説明、コミットの代表preview、対象素材との関連付けを持たせる。関連付けはTASK-83の不変file_idを利用し、素材の改名・移動後も同一性を保つ。サムネイル画像の生成や自動置換、音声・動画・3D表示機能は本件に含めない。保存形式の変更はTASK-80に従う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 previewごとに表示名と説明を設定・編集・解除でき、元ファイル名・添付ID・原本の内容とは独立して保持する。未設定時の表示、文字数・改行などの規則が明確である
- [ ] #2 コミットごとに代表previewを最大1件指定・変更・解除でき、GUIで識別できる。同じコミットに属するpreviewだけを指定でき、未指定時の表示が明確である
- [ ] #3 previewをそのコミット内の対象素材へfile_idで関連付け・解除でき、GUIから対象を確認できる。複数素材への対応範囲を定義し、改名・移動や同名の別素材で関連を混同しない
- [ ] #4 previewの置き換え・並べ替え・削除、素材の削除、葉の削除/取り消し時の表示名・説明・代表指定・素材参照の扱いを定義し、無効な参照を残さない。代表指定でサムネイルの原本や未選択メディアの自動読み込みを変更しない
- [ ] #5 CLI・JSON・GUIからメタ情報を確認・更新でき、archiveにも保存する。失敗した更新は既存の添付内容・順序・関連情報を部分的に変更しない
- [ ] #6 未設定、設定・解除、他コミットや存在しない添付/素材の指定、改名・移動、置換・削除・取り消し、再オープンと更新失敗を自動テストで検証し、READMEを更新する
<!-- AC:END -->
