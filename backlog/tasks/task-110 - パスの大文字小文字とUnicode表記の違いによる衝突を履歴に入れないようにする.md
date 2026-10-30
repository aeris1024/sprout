---
id: TASK-110
title: パスの大文字小文字とUnicode表記の違いによる衝突を履歴に入れないようにする
status: To Do
assignee: []
created_date: '2026-10-30 18:06'
updated_date: '2026-10-30 18:07'
labels:
  - storage
  - v1
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - README.md
priority: high
type: bug
ordinal: 109000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Windowsで`Logo.png`をエクスプローラーで`logo.png`へ改名すると`status`は変更なしのままで、`sprout track logo.png`して保存すると、1つのファイルが別の素材IDを持つ2つのパスとしてコミットに記録される。以後は`go`が前の版にも最新版にも「restore recovery conflict」で失敗し、`export`も失敗するが、`status`と`doctor`は正常と表示する。一度入ったコミットはWindowsで正しく展開できず、後から修復できない。`sprout move A.txt a.txt`も「移動先が既に存在する」と拒否され、正しい改名手段がない。NFDのパスも正規化されずに保存される。アプリは未運用のため、V1の保存形式を直接変更してよい。形式番号は1のままとし、旧構造からの移行は用意しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 追跡パス、コミットのファイル、つぼみのファイルのいずれでも、NFC正規化と大文字小文字の同一視で同じになるパスをDBの制約で保存できない
- [ ] #2 衝突するパスの登録はOSを問わず拒否され、対象のパスと理由を含むエラーになる。作業ファイルと履歴は変更しない
- [ ] #3 `sprout move`で大文字小文字や表記だけの改名ができ、素材IDを維持し、改名前後の履歴がつながる
- [ ] #4 外部で大文字小文字だけを改名した場合に`status`で検出でき、素材IDを維持して記録できる
- [ ] #5 保存時の表記（大文字小文字など）は表示と復元で維持される
- [ ] #6 `doctor`が衝突するパスを検出する
- [ ] #7 自動テストで改名、衝突、つぼみ、復元、export、NFDのパスを検証し、README.mdとV1のスキーマ検査を更新する
<!-- AC:END -->
