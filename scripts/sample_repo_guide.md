# Sproutサンプルリポジトリ ガイド

「春の芽吹きマルシェ」のポスター制作を模したサンプルです。コマンドはこのフォルダで実行します。コミットIDは生成ごとに変わるため、手順ではタグ名とブランチ名を使います。

```text
ラフ案 (first-draft) ─ 配色調整 ─ ロゴ追加 ─ 修正反映 (submitted) ─ ロゴ整理 ← main
                          │                     ├─ ロゴ配色 ← logo-test
                          │                     └─ 没案（abandoned。枝は削除済み）
                          └─ 夜祭り配色 ─ 星空 ← night
```

## GUIで見る

Sprout GUIでこのフォルダを開くと、サムネイル付きのコミットツリーを確認できます。`submitted`のコミットを選ぶと、画像・音声・3Dモデルのpreview、メモ、ラベルも表示されます。

## 1. 履歴を眺める

```powershell
sprout tree
sprout log --oneline
sprout show submitted --timezone local
sprout log --label submitted
sprout log poster.png --oneline
```

`tree`には、ブランチを削除した`abandoned`のコミットも`created:abandoned`として残っています。

## 2. 状態を確認する

```powershell
sprout status --tracked --untracked
```

`scratch-idea.txt`は未追跡です。`cache/`と`GUIDE.md`は`.sproutignore`で除外されるため表示されません。

## 3. ゴミ箱から復旧する

`main`の先端にあった「誤って保存した版」がゴミ箱に入っています。復旧は現在位置やブランチ先端が削除直後のままのときだけできるので、編集や移動の前に試します。

```powershell
sprout trash list
sprout trash restore <trash-id> --dry-run
sprout trash restore <trash-id>
sprout log --oneline
```

作業ファイルは変更されないため、復旧したコミットとの差分が未保存の変更として表示されます。確認したら、もう一度その葉を削除して元の状態へ戻します。

```powershell
sprout status
sprout delete-commit main --dry-run
sprout delete-commit main --yes
sprout restore main --discard
```

## 4. 差分を見る

```powershell
sprout diff first-draft submitted
```

## 5. 編集してコミットする

```powershell
Add-Content brief.md "- 追記: 雨天決行" -Encoding utf8
sprout status
sprout diff
sprout commit -m "雨天時の案内を追記"
```

## 6. 別案へ切り替える

`night`へ切り替えると、`poster.png`が夜祭り版に変わります。画像を開いて確かめてみてください。

```powershell
sprout switch night
sprout switch main
```

## 7. 未保存の変更の保護とつぼみ

未保存の変更があると、`switch`は作業を守るために中止します。`go`なら変更を「つぼみ」として残して移動します。

```powershell
Add-Content brief.md "- 追記: 試しの変更" -Encoding utf8
sprout switch night
sprout go night
sprout bud
```

一覧に、今残したつぼみと、最初から入っている「配布用チラシ」のつぼみが並びます。先頭に表示されるIDを指定すると戻せます。

```powershell
sprout go main
sprout bud --restore <bud-id>
sprout restore main --discard
```

## 8. 一部のファイルだけ昔に戻す

```powershell
sprout restore first-draft palette.json
sprout status
sprout restore main --discard
```

## 9. previewとメモ

```powershell
sprout preview list submitted
sprout note submitted
sprout label submitted
```

## 10. 改名をまたぐ履歴

`assets/brand/logo.png`は`assets/logo.png`から移動したファイルです。`show`で`file_id`を確認して指定します。

```powershell
sprout show main --json
sprout file-history <file-id>
```

## 11. 取り出しと保守

`export`は親フォルダへファイルを書き出します。それ以外は`--dry-run`や読み取り専用のコマンドなので、履歴は変わりません。

```powershell
sprout export submitted --output ../sprout-sample-export
sprout archive --output ../sprout-sample-archive --dry-run
sprout prune first-draft submitted --dry-run
sprout gc --dry-run
sprout stats
sprout doctor
```

## やり直す

履歴はこのフォルダの`.sprout`にあります。最初からやり直す場合は、このフォルダを削除してSproutのリポジトリで生成し直してください。

```powershell
uv run python scripts/create_sample_repo.py <出力先フォルダ>
```
