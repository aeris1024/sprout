---
id: TASK-125
title: CLIをleaf・bud・branch・file中心の構成と手打ち用aliasへ整理する
status: To Do
assignee: []
created_date: '2026-10-31 07:21'
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
合意したCLI体系への再編を管理する親タスク。機能削減ではなく、対象別の正規コマンドと手打ち用aliasを設け、現在の33トップレベルコマンドの機能をすべて配置し直す。実装タスクの登録のみが現在の依頼であり、実装は別途着手する。

正規トップレベルは init / status / go / leaf / bud / branch / file / trash / maintenance / serve の10入口。通常ヘルプは正規体系を中心に表示し、aliasの対応表を別途確認できるようにする。GUIにもこの正規体系を使わせる。

合意した正規構成:
- leaf create -m TEXT / list [PATH] / tree / show LEAF / edit LEAF --message TEXT / restore LEAF / delete LEAF / prune START_TAG END_TAG または --all / archive --output DIR
- leaf note show|set|delete、leaf label list|add|delete、leaf tag list|create|comment|delete
- leaf thumbnail show|set|delete|export、leaf preview list|add|replace|delete|export|order|edit|image。preview editは現在のmetadataに対応。
- bud save [--name NAME] [--keep-files] / list / restore BUD / rename BUD NAME / delete BUD
- branch list [--deleted] / create NAME [LEAF] / switch NAME / rename OLD NEW / comment NAME TEXT / delete NAME
- file track PATH... / untrack PATH... / list / move OLD NEW / history FILE_ID / diff [LEAF_A] [LEAF_B] / restore LEAF PATH... / export LEAF [PATH...] --output DIR / cat LEAF PATH
- file cover show / set IMAGE / clear / apply
- trash list / show ID / restore ID / purge ID、maintenance stats / doctor / gc
- init [PATH]、status [PATH...]、go TARGET、serveはトップレベルのまま。

手打ちalias:
commit -m TEXT -> leaf create -m TEXT
log [PATH] -> leaf list [PATH]
show LEAF -> leaf show LEAF
tree -> leaf tree
diff ... -> file diff ...
track PATH... -> file track PATH...
untrack PATH... -> file untrack PATH...
mv OLD NEW -> file move OLD NEW
switch NAME -> branch switch NAME
stash push -> bud save
stash list -> bud list
stash pop BUD -> bud restore BUD
stash drop BUD -> bud delete BUD
tag -> leaf tag list
tag NAME [LEAF] -> leaf tag create NAME [LEAF]

共通の範囲:
- 各機能に現在存在するJSON、dry-run、確認、上書き、日時、絞り込み、コメント等のオプションを対応先で維持する。バイナリ標準出力も維持。
- go、branch switch、leaf restore、file restoreは既存の異なる意味を保持する。未保存変更の退避・拒否・破棄、ブランチ選択、現在位置更新の方針統合は今回の範囲外。
- prune（タグ間・全履歴）を高度な履歴整理として残す。previewの代表指定・素材関連付けも残す。
- 保存形式は現行V1のまま。schema変更や保存データの移行、保存形式の旧版互換処理の追加は不要。
- aliasはSproutの動作を呼び出す別名。Gitのステージングやstash applyを追加する要件ではない。alias表にない全旧構文の恒久的な互換維持を要件にはしない。段階的な実装中は既存GUIが使える状態を維持し、最終的にGUI・スクリプト・文書・補完を正規構文へそろえる。
- この親子タスクはCLI体系の再編を扱う。既存GUI機能の追加タスクやプレビュー機能削減、GUIの用語・画面再設計は含めない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 合意した10入口の正規体系に現行33トップレベルコマンドと各下位操作の機能がすべて対応し、各子タスクから現在と新構文の対応を追える
- [ ] #2 指定した手打ちaliasが正規構文と同じ引数解釈・処理結果・JSON・終了コード・確認動作で利用できる
- [ ] #3 現在のV1保存形式と各操作の意味・安全確認を維持し、pruneやpreviewの機能を削減しない
- [ ] #4 GUIの都度起動とserve経由の操作、サンプル生成、ヘルプ・補完・READMEが新体系で整合し、対応する検証が成功する
<!-- AC:END -->
