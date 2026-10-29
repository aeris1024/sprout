---
id: TASK-76
title: GUIの葉削除で確認ダイアログが開かない不具合を修正する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-29T16:18:00Z'
updated_date: '2026-10-29T16:21:00Z'
labels: []
dependencies: []
priority: high
type: bug
ordinal: 75000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
葉削除はdry-runの後にTauriのconfirmを呼ぶが、mainウィンドウにdialog:allow-messageがなくIPCが拒否される。ダイアログをモックする既存テストでは権限漏れを検出できない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 mainウィンドウで削除確認に必要なダイアログ権限が許可される
- [x] #2 確認ダイアログを開けない場合はエラーを通知し、削除を実行しない
- [x] #3 権限設定と確認失敗の回帰テストが成功し、既存の削除・キャンセルのテストも成功する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. confirmのmessage IPCと権限の不一致を確認。2. 権限設定と確認失敗の回帰テストを追加して失敗を確認。3. allow-messageを追加し葉削除全体をexecuteで囲む。4. GUIテストとビルド、CLI削除テスト後にmainへff-onlyで取り込みpush。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
原因: インストール済みplugin-dialogのconfirmはplugin:dialog|messageを呼び、Rustプラグインのallow-messageがmessageコマンドを許可する。default capabilityにはallow-openしかなく確認IPCが拒否される。さらにconfirmがexecute外なので拒否が未処理Promiseとなり画面に出なかった。回帰テストを先に実行して2件失敗と未処理拒否を確認し、権限追加とdry-runから確認・削除までのexecute共通化で修正。確認待ちもbusyを維持する。検証: pnpm test 65 passed、pnpm build成功、cargo test 6 passed、tests/test_delete_commit.py 9 passed。一時ディレクトリ制限によるpytest初期化エラーは通常権限で再実行し解消。ネイティブGUI実機操作は未実施。インストール済みGUIへの反映には再ビルド・再インストールが必要。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GUIの葉削除が確認ダイアログの権限不足で止まる問題を修正。dialog:allow-messageを追加し、確認ダイアログ失敗も通知して削除せず再試行できるようにした。権限設定と確認失敗の回帰テストを追加。GUI 65件、Rust 6件、CLI削除9件成功、GUIビルド成功。
<!-- SECTION:FINAL_SUMMARY:END -->
