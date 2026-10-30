---
id: TASK-93
title: Sproutを試せるサンプルリポジトリの生成スクリプトを追加する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 17:39'
updated_date: '2026-10-30 17:49'
labels: []
dependencies: []
priority: medium
type: feature
ordinal: 92000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Sproutの主要機能（履歴・分岐・タグ・サムネイル・preview・つぼみ・ゴミ箱）をすぐに試せるよう、制作プロジェクトを模したサンプルのSproutリポジトリを生成できるようにする。.sproutはバイナリを含み手動編集しないものなのでGitへ入れず、実際のCLIで毎回生成する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 1つのコマンドで、既存データを壊さずに指定フォルダへサンプルリポジトリを生成できる
- [x] #2 生成結果にブランチ分岐、タグ、サムネイル、preview、メモ、ラベル、つぼみ、ゴミ箱項目、削除済みブランチ由来のコミット、移動履歴が含まれ、doctorが成功する
- [x] #3 READMEに生成方法が記載され、自動テストが生成結果を検証する
- [x] #4 生成物にCLIとGUIで試す手順のガイドが含まれ、CLIの手順が実際に動作する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. scripts/create_sample_repo.py で素材を生成しながら実CLIを呼んで履歴を作る
2. 手順書 scripts/sample_repo_guide.md を GUIDE.md としてコピーする（.sproutignoreで除外）
3. 空でない出力先は拒否して既存データを守る
4. ゴミ箱の復旧は現在位置が変わると拒否されるため、葉の削除を生成の最後に行い、ガイドでも編集・移動の前に試す
5. tests/test_sample_repo.py で生成結果を検証し、README に追記する
6. ガイドの全コマンドを実行して確認する
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ガイドのCLI手順はインストール済みCLIで新規生成のサンプルに対して実行して確認した。GUIでの表示は未確認（GUIの節はフォルダを開く案内のみ）。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
サンプル生成スクリプト scripts/create_sample_repo.py と手順書を追加し、READMEに生成方法を記載した。uv run pytest（513 passed, 19 skipped）と、ガイドのCLI手順の実行で確認した。GUIでの表示は未確認。
<!-- SECTION:FINAL_SUMMARY:END -->
