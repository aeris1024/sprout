---
id: TASK-82
title: 葉とpreviewの削除・置き換えを取り消せるようにする
status: To Do
assignee: []
created_date: '2026-10-29T19:07:00Z'
labels: []
dependencies:
  - TASK-80
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - gui/src/App.tsx
  - gui/src/components/CommitPanel.tsx
  - gui/src/components/PreviewPanel.tsx
  - tests/test_delete_commit.py
  - tests/test_previews.py
  - tests/test_v1_storage.py
priority: high
type: feature
ordinal: 81000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在はdelete-commitで葉のファイル一覧・添付・メモ・ラベルを削除し、子の親やブランチ先端・現在位置・つぼみ起点も付け替える。previewの削除や置き換え前の内容も操作から戻せず、gcで実体を回収すると復旧できない。制作中の誤操作から回復できるよう、葉とpreviewの削除をゴミ箱から復元し、previewの置き換え前の版へ戻せる機能を追加する。対象は単一の葉の削除、previewの削除・置き換えとし、全操作共通Undo、ブランチ・タグ・メモ・ラベル単体の編集履歴は本件に含めない。非互換構造の扱いはTASK-80に従う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 削除した単一の葉とpreviewを復旧可能な項目として一覧・識別でき、再起動後も取り消しできる。通常の履歴・添付一覧とは区別する
- [ ] #2 葉の削除を取り消す際、保存ファイル・添付・メモ・ラベルと、削除時に変化した親子関係・ブランチ先端・現在位置・つぼみ起点を復旧できる。作業ファイルは無断で変更しない
- [ ] #3 削除後の追加操作と参照変更を検査し、後から進めた履歴や同名の別対象を上書きしない。安全に取り消せない場合は理由を示し、部分的な復旧を確定しない
- [ ] #4 previewの削除取り消しと置き換え前の版への復帰で、対象の添付ID・内容・元ファイル名・media_type・サイズ・表示順・日時を定義した規則で復旧する。他の添付と順序を壊さない
- [ ] #5 復旧可能な項目が必要とするオブジェクトはgcで回収しない。完全削除・保持期限・容量表示・pruneやarchiveでの扱いを明文化し、完全削除前に対象と回収可能容量を確認できる
- [ ] #6 CLI・JSON・GUIから対象の確認、復旧、完全削除を行える。破壊的操作には影響と取り消せる範囲を示し、失敗時は構造化エラーを表示する
- [ ] #7 ルート/中間/現在位置/枝先の葉、添付削除・複数回の置き換え、再起動、後続操作との競合、gc保護と完全削除、失敗・中断時の整合性を自動テストで検証し、READMEを更新する
<!-- AC:END -->
