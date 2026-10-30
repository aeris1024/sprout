---
id: TASK-97
title: GUIで画面に見えていない葉をドロップや貼り付けで変更しないようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:53'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/App.tsx
  - gui/src/components/PreviewPanel.tsx
  - gui/README.md
priority: high
type: bug
ordinal: 96000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ファイルのドロップと画像の貼り付けの対象は、表示中のパネルではなく選択中の葉で決まる。ゴミ箱パネルを表示中でも、葉を選択していればドロップはその葉のプレビューに追加され、画像の貼り付けはサムネイルを確認なしで置き換える。テキスト入力欄で画像を貼り付けた場合も同様に置き換わる。コードの確認による判断で、実機での再現が必要。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ゴミ箱パネルなど葉の詳細以外を表示中は、ドロップと貼り付けで表示されていない葉を変更しない
- [ ] #2 ドロップ中に、追加先が分かる表示が出る
- [ ] #3 既存のサムネイルを貼り付けで置き換える前に、置き換えることが確認でき、取り消せる
- [ ] #4 メモやメッセージなどのテキスト入力欄で画像を貼り付けても、意図せずサムネイルを変更しない
- [ ] #5 自動テストで表示中のパネルごとの動作を検証し、実機でドロップと貼り付けを確認して、gui/README.mdを更新する
<!-- AC:END -->
