# Sprout

Sproutは、ローカルファイルを対象とするスナップショット型のバージョン管理CLIです。
指定した複数のファイルをコミット単位で保存し、任意のコミットへの復元とブランチによる履歴の分岐を提供します。
管理データはローカルディスク内に保存され、ネットワーク通信を必要としません。

## 特徴

- 複数のファイルをまとめて1つのコミットとして保存
- 過去のコミットをいつでも復元
- ブランチを使って作業を分岐
- 同じ内容のファイルは重複して保存しない
- 未コミットの変更や未追跡ファイルを保護
- オフラインで完結

Sproutはファイルの差分ではなく、その時点のファイル構成をスナップショットとして記録します。

## インストール

Python 3.12以降が必要です。[uv](https://docs.astral.sh/uv/)を利用すると、次のコマンドで開発環境を準備できます。

```powershell
uv sync --dev
uv run sprout --help
```

通常のコマンドとしてインストールする場合は、プロジェクトのルートで次を実行します。

```powershell
uv tool install .
sprout --help
```

## クイックスタート

まず、管理したいフォルダへ移動してSproutを初期化します。

```powershell
sprout init
```

次に、保存したいファイルやフォルダを追跡対象へ登録します。フォルダを指定した場合は、その中にあるファイルがまとめて登録されます。

```powershell
sprout track document.bin references
sprout status
```

作業の区切りでコミットを作成します。

```powershell
sprout commit -m "最初のスナップショット"
```

保存した履歴は、次のコマンドで確認できます。

```powershell
sprout log
sprout show <commit-id>
```

## ブランチを使う

現在の状態から別の作業を試したいときは、ブランチを作成します。
ブランチは最初のコミット後に作成できます。

```powershell
sprout branch experiment -m "別の方法を試す"
sprout switch experiment
```

ブランチの一覧は`sprout branch`で確認できます。先頭に`*`が付いているものが現在のブランチです。

```text
* main                 a12bc34de567
  experiment           b98fe76dc543  # 別の方法を試す
```

## 過去の状態へ戻る

ブランチを切り替える場合は`switch`、特定のコミットを作業フォルダへ復元する場合は`restore`を使います。

```powershell
sprout switch main
sprout restore <commit-id>
```

未保存の変更がある場合、Sproutはファイルを保護するため処理を中止します。
変更を破棄してよい場合に限り、`--discard`を指定してください。

```powershell
sprout switch main --discard
```

`--discard`を指定しても、未追跡ファイルが上書きされることはありません。
また、まだ一度もコミットされていない追跡ファイルが削除される場合も処理を中止します。
作業フォルダが保存済みコミットの内容そのものなら、別のコミットやブランチへ戻るときに`--discard`は不要です。

古いコミットを確認したあと現在のブランチの最新状態に戻るには、ブランチ名を指定して復元します。

```powershell
sprout restore main
```

## ファイルの追跡状態を確認する

```powershell
# 変更された追跡ファイルを表示
sprout status

# 特定のファイルが追跡されているか確認
sprout status document.bin

# 追跡済み、未追跡のファイルを一覧表示
sprout status --tracked
sprout status --untracked
```

ファイルの追跡をやめる場合は`untrack`を使用します。作業フォルダのファイル自体は削除されません。

```powershell
sprout untrack document.bin
```

追跡済みファイルの名前や場所を変える場合は`move`を使用します。
作業フォルダのファイルを移動し、追跡パスも更新します。

```powershell
sprout move document.bin archive/document.bin
sprout commit -m "ファイルを移動"
```

`status`と`commit`はファイル内容で変更を判定します。
内容が同じで更新時刻だけが変わったファイルは、変更なしとして扱われます。

## データの保存場所

履歴は、初期化したフォルダ内の`.sprout`へ保存されます。バックアップや別のディスクへ移動するときは、`.sprout`を含めてフォルダ全体をコピーしてください。

`.sprout`の内容は手動で編集しないでください。処理が途中で中断された場合は、次回のSprout起動時に可能な範囲で自動的に復旧します。

## コマンド一覧

| コマンド | 説明 |
| --- | --- |
| `init [PATH]` | Sproutの管理情報を作成する |
| `track PATH...` | ファイルを追跡対象へ登録する |
| `untrack PATH...` | ファイルの追跡をやめる |
| `move OLD NEW` | 追跡済みファイルを移動する |
| `status` | 現在の変更や追跡状態を確認する |
| `commit -m MESSAGE` | 現在の状態をコミットする |
| `log` | 現在のブランチの履歴を表示する |
| `show COMMIT` | コミットの詳細を表示する |
| `branch [NAME]` | ブランチの一覧表示または作成を行う |
| `switch BRANCH` | 別のブランチへ切り替える |
| `restore COMMIT` | 指定したコミットを復元する |

コミットの指定には、完全なコミットID、一意に識別できるIDの先頭部分、またはブランチ名を使用できます。

## 現在の制限

最初のリリースでは、リモート同期、マージ、タグ、ファイル差分、GUIには対応していません。
不要になったオブジェクトを削除するGCもまだありません。
大きなファイルを頻繁に更新すると、`.sprout/objects`の使用量が増え続けます。

## テスト

```powershell
uv run pytest
```

## ライセンス

Sproutは[MIT License](LICENSE)のもとで公開されています。
