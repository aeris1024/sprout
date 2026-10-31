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
sprout leaf tree
sprout leaf list --oneline
sprout leaf show submitted --timezone local
sprout leaf list --label submitted
sprout leaf list poster.png --oneline
```

`leaf tree`には、ブランチを削除した`abandoned`のコミットも`created:abandoned`として残っています。

## 2. 状態を確認する

```powershell
sprout status --tracked --untracked
```

`scratch-idea.txt`は未追跡です。`cache/`と`GUIDE.md`は`.sproutignore`で除外されるため表示されません。

## 3. ゴミ箱から復旧する

`--discard`で破棄した変更も同じ一覧に`discard`として並び、復旧するとつぼみとして戻ります。削除したメモ・タグ・ブランチも同じ一覧から戻せます。

`main`の先端にあった「誤って保存した版」がゴミ箱に入っています。復旧は現在位置やブランチ先端が削除直後のままのときだけできるので、編集や移動の前に試します。

```powershell
sprout trash list
sprout trash restore <trash-id> --dry-run
sprout trash restore <trash-id>
sprout leaf list --oneline
```

作業ファイルは変更されないため、復旧したコミットとの差分が未保存の変更として表示されます。確認したら、もう一度その葉を削除して元の状態へ戻します。

```powershell
sprout status
sprout leaf delete main --dry-run
sprout leaf delete main --yes
sprout go --branch main --discard
```

## 4. 差分を見る

```powershell
sprout file diff first-draft submitted
```

## 5. 編集してコミットする

```powershell
Add-Content brief.md "- 追記: 雨天決行" -Encoding utf8
sprout status
sprout file diff
sprout leaf create -m "雨天時の案内を追記"
```

## 6. 別案へ切り替える

`night`へ切り替えると、`poster.png`が夜祭り版に変わります。画像を開いて確かめてみてください。

```powershell
sprout go --branch night
sprout go --branch main
```

## 7. 未保存の変更の保護とつぼみ

未保存の変更があると、`go`は変更を「つぼみ」として残して移動します。変更がある場合に移動を中止したいときは`--reject-changes`を指定します。

```powershell
Add-Content brief.md "- 追記: 試しの変更" -Encoding utf8
sprout go --branch night --reject-changes
sprout go --branch night
sprout bud list
```

一覧に、今残したつぼみと、最初から入っている「配布用チラシ」のつぼみが並びます。先頭に表示されるIDを指定すると戻せます。

```powershell
sprout go --branch main
sprout bud restore <bud-id>
sprout go --branch main --discard
```

## 8. 一部のファイルだけ昔に戻す

```powershell
sprout file restore first-draft palette.json
sprout status
sprout go --branch main --discard
```

## 9. previewとメモ

```powershell
sprout leaf preview list submitted
sprout leaf show submitted
sprout leaf label list submitted
```

## 10. 改名をまたぐ履歴

`assets/brand/logo.png`は`assets/logo.png`から移動したファイルです。`leaf show`で`file_id`を確認して指定します。

```powershell
sprout leaf show main --json
sprout leaf list --file-id <file-id>
```

## 11. 取り出しと保守

`file export`は親フォルダへファイルを書き出します。それ以外は`--dry-run`や読み取り専用のコマンドなので、履歴は変わりません。

```powershell
sprout file export submitted --output ../sprout-sample-export
sprout leaf archive --output ../sprout-sample-archive --dry-run
sprout leaf prune first-draft submitted --dry-run
sprout maintenance gc --dry-run
sprout maintenance stats
sprout maintenance doctor
```

## やり直す

履歴はこのフォルダの`.sprout`にあります。最初からやり直す場合は、このフォルダを削除してSproutのリポジトリで生成し直してください。

```powershell
uv run python scripts/create_sample_repo.py <出力先フォルダ>
```
