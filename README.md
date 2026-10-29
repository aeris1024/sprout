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

### シェル補完

コマンド名、オプション、ブランチ名、タグ名をTabキーで補完できます。利用するシェル内でインストールコマンドを実行し、その後ターミナルを再起動してください。現在のシェルは自動検出されます。

PowerShell:

```powershell
sprout --install-completion
```

bash:

```bash
sprout --install-completion
```

zsh:

```zsh
sprout --install-completion
```

設定ファイルへ書き込まず補完スクリプトだけ確認したい場合は、各シェル内で次を実行します。

```text
sprout --show-completion
```

## デスクトップGUI

`gui/`にはTauri 2 + React + TypeScript + Viteで構築したWindows向けGUIがあります。GUIはSproutの管理データへ直接触れず、PATHまたは設定画面で指定したCLIを`--json`付きで呼び出します。

```powershell
cd gui
pnpm install
pnpm tauri dev
```

フォルダ選択と初期化、追跡・追跡解除、サムネイル付きコミット、履歴・コミット詳細、全ブランチのサムネイル付きコミットツリー、ブランチ作成・切り替え、復元、構造化エラー通知、最近使ったプロジェクトの保存に対応しています。必要なNode.js、Rust、Visual Studio環境、詳しい操作方法とビルド手順は[gui/README.md](gui/README.md)を参照してください。

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

コミットへ小さな静止画像を付ける場合は`--thumbnail`を指定します。PNG、JPEG、WebPに対応し、ファイルサイズは2 MiB以下、幅と高さはそれぞれ4096ピクセル以下に制限されます。画像は実際の内容をデコードして検証され、破損画像、アニメーション画像、拡張子だけを変更した非画像ファイルは拒否されます。

```powershell
sprout commit -m "色を調整" --thumbnail preview.png
```

保存した履歴は、次のコマンドで確認できます。

```powershell
sprout log
sprout log scene.blend
sprout show <commit-id>
sprout tree
```

`sprout log` にパスを指定すると、そのファイル内容が変わったコミットだけを表示します。内容が同じままのコミットは省かれます。一度も登場していないパスでは `No history for path:` と表示されます。
表示件数は`-n/--max-count`で制限でき、`--oneline`を指定すると各コミットを1行で表示できます。

```powershell
sprout log -n 5
sprout log --oneline
sprout log scene.blend -n 5 --oneline
sprout log --label submitted
```

`--label`は前後の空白とUnicode表現を正規化したうえで、ラベルの大文字小文字を区別して完全一致検索します。パス、件数、表示形式の指定とも併用できます。

`sprout show`のコミット日時とファイル更新日時は、既定ではUTCで表示されます。ローカルタイム、またはIANAタイムゾーン名を指定することもできます。

```powershell
sprout show <commit-id> --timezone local
sprout show <commit-id> --timezone Asia/Tokyo
```

## ブランチを使う

現在の状態から別の作業を試したいときは、ブランチを作成します。
ブランチは最初のコミット後に作成できます。

```powershell
sprout branch experiment -m "別の方法を試す"
sprout switch experiment
```

過去のコミットから分岐したいときは、ブランチ名のあとに起点を指定します。コミットID（または先頭部分）、ブランチ名、タグ名を使えます。`--switch`を付けると、作成したブランチへ切り替わり、作業ツリーもその起点の内容になります。

```powershell
# 過去のコミットからブランチを作るだけ
sprout branch rethink <commit-id>

# 作成してすぐ切り替える
sprout branch rethink <commit-id> --switch

# タグや別ブランチを起点にする
sprout branch from-tag submitted --switch
sprout branch from-main main
```

起点を省略した場合は、現在のブランチ先端から作成します。ただし`restore`で先端とは異なる保存済みスナップショットへ移動しているとき（現在位置が先端以外のとき）に起点を省略すると、移動後にファイルを編集していても、誤って最新から分岐しないようエラーになります。その場合は起点を明示してください。

```powershell
sprout restore <commit-id>
# エラーになる（先端から暗黙に分岐しない）
sprout branch rethink
# 正しい指定
sprout branch rethink <commit-id> --switch
```

ブランチの一覧は`sprout branch`で確認できます。先頭に`*`が付いているものが現在のブランチです。

```text
* main                 a12bc34de567
  experiment           b98fe76dc543  # 別の方法を試す
```

ブランチ名を変更する場合は、現在の名前を位置引数、新しい名前を`--rename`へ指定します。現在のブランチを変更した場合も、そのブランチを選択した状態が保たれます。不要なブランチは`--delete`で削除できますが、現在のブランチは削除できません。

```powershell
sprout branch experiment --rename prototype
sprout branch --delete prototype
```

## タグを使う

動かない目印をコミットへ付けたい場合はタグを使用します。コミットを省略すると現在のブランチの先端、指定するとそのコミットへタグを作成します。コミットの代わりにブランチ名や既存タグ名も指定できます。

```powershell
# 現在のコミットにタグを作成
sprout tag submitted -m "提出版"

# 過去のコミットにタグを作成
sprout tag first-draft <commit-id> -m "初稿"

# コメントの変更（空文字でコメントを消す）
sprout tag first-draft --set-comment "初稿（差し戻し前）"

# 一覧と削除
sprout tag
sprout tag --delete first-draft
```

タグ名は`show`や`restore`など、コミットを受け取るコマンドで使用できます。

```powershell
sprout show submitted
sprout restore submitted
```

## リポジトリ全体の履歴を見る

`log`は現在のブランチだけをたどります。分岐した履歴や、削除済みブランチから作られたコミットを含む全履歴を見る場合は`tree`を使います。

```powershell
sprout tree
```

人間向け表示は古いコミットから新しいコミットへ親子関係をASCII枝で示します。`created`はコミット作成時のブランチ名、`branch`と`tag`は現在そのコミットを指す参照です。現在のブランチには`*`が付きます。サムネイル、メモ、ラベルもマーカーで確認できます。

```text
* a12bc34de567 initial [created:main] [tag:baseline]
|- * b23cd45ef678 main work [created:main] [branch:*main]
`- * c34de56fa789 side work [created:side] [thumbnail] [note] [labels:Candidate]
```

削除したブランチ名は現在の`branch`参照から消えますが、そのブランチで作成したコミットと`created`の値は保持されます。GUIや外部ツールから利用する場合は`tree --json`で平坦なコミット配列と現在の参照を取得できます。人間向けツリーは古い順、JSONの`commits`配列は新しい順です。

## 履歴を間引く

制作途中のタグなしコミットを削除する場合は`prune`を使います。2つのタグを古い順に指定するタグ間モードでは、その祖先経路内にあるタグなし中間コミットだけが対象です。すべてのタグ付きコミット、現在存在する各ブランチの先端、作業ツリーの現在位置のコミットは常に保護されます。

```powershell
# 変更せずに削除対象と、gcで回収可能になる容量を確認
sprout prune first-draft submitted --dry-run

# 確認したタグ間を実際に間引く
sprout prune first-draft submitted --yes
```

全履歴モードは、タグ付きコミットと現存ブランチ先端以外をすべて削除します。削除済みブランチ由来で、タグも現存ブランチ参照もないコミットも対象になります。

```powershell
sprout prune --all --dry-run
sprout prune --all --yes
```

`prune`は取り消せません。実行には`--yes`が必要で、削除後は残したコミットの親が元の履歴上で最も近い残存祖先へ接続されます。部分復元などで作業ツリーの内容が削除対象の過去コミットと一致する場合は、そのコミットへタグを付けるかブランチを作成するまで実行を拒否します。コミット削除だけではobjectsのファイルやSQLiteデータベース自体のサイズは縮まらないため、表示された容量を実際に回収するには続けて`sprout gc`を実行してください。SQLiteの`VACUUM`は行いません。

## 過去の状態へ戻る

ブランチを切り替える場合は`switch`、特定のコミットを作業フォルダへ復元する場合は`restore`を使います。

```powershell
sprout switch main
sprout restore <commit-id>
```

復元や切り替えの前に、ファイル単位の差分だけ確認したい場合は`diff`を使います。

```powershell
# 現在位置と作業ツリー
sprout diff

# 指定コミットと作業ツリー
sprout diff <commit-id>

# コミット間（A から B）
sprout diff <commit-a> <commit-b>
```

特定のファイルだけ昔の版に戻す場合は、コミットのあとにパスを指定します。ディレクトリを指定すると、そのコミット内の配下ファイルがまとめて復元されます。部分復元ではブランチ先端や、指定していない追跡ファイルの状態は変わりません。

```powershell
sprout restore <commit-id> docs/manual.bin
sprout restore <commit-id> assets/
```

未保存の変更がある場合、Sproutはファイルを保護するため処理を中止します。
変更を破棄してよい場合に限り、`--discard`を指定してください。
部分復元では、復元対象のパスに未保存変更があるときだけ`--discard`が必要です。

```powershell
sprout switch main --discard
```

`--discard`は、新たに追跡したファイルや移動したファイルを含む、追跡済みファイルのすべての未コミット変更を破棄します。
未追跡ファイルを削除したり上書きしたりすることはなく、復元先のパスと未追跡ファイルが衝突する場合は処理を中止します。
作業フォルダが保存済みコミットの内容そのものなら、別のコミットやブランチへ戻るときに`--discard`は不要です。

復元対象やその親ディレクトリにシンボリックリンク（リンク切れを含む）やWindowsのジャンクションがある場合は、リンク先がプロジェクト内でも復元を拒否します。`--discard`でもこの検査は省略されません。`switch`と`branch --switch`にも同じ保護が適用されます。

全体復元では、たとえば`asset`というファイルと`asset/data.bin`というフォルダ構成の間を行き来できます。構成変更に必要な追跡ファイルを退避し、空になったディレクトリだけを除去してから配置します。衝突箇所に未追跡ファイルや未追跡の空ディレクトリがある場合は中止します。部分復元で選択外の追跡ファイルの移動・削除が必要になる場合も中止するため、その場合は全体復元を使ってください。

復元途中で中断された場合は、次の起動時に記録済みの操作を巻き戻します。復旧途中の再中断にも対応し、復旧が完了するまで退避ファイルを保持します。復旧先にリンクや新たなファイルの衝突が見つかった場合は、自動復旧を止め、原因のパスを表示します。必要な作業ファイルを別の場所へ保存し、衝突やリンクへの置き換えを解消してからSproutを再実行してください。復旧完了前に`.sprout/tmp`を削除しないでください。復元・復旧の実行中は、他のアプリでファイルやディレクトリ構成を変更しないでください。

古いコミットを確認したあと現在のブランチの最新状態に戻るには、ブランチ名を指定して復元します。

```powershell
sprout restore main
```

Sproutは、作業ツリーがどのスナップショットに基づいているかを「現在位置」として記録します。全体の`restore`、`switch`、`branch --switch`、`go`、つぼみの復元、`commit`が成功すると現在位置が更新されます。部分復元、失敗した操作、中断後に巻き戻された操作では更新されません。`status`の変更一覧、引数なしの`diff`、移動前の未保存変更の判定は、ブランチ先端ではなく現在位置と作業ツリーを比べます。そのため、過去のスナップショットへ移動した直後は変更なしと表示され、編集しなければ`--discard`なしで別のスナップショットへ移動できます。現在位置がブランチ先端以外のとき、`status`は`Viewing saved snapshot <id> (not the branch tip)`と表示し、`tree`は該当コミットに`current`を付けます。現在位置は専用の状態テーブルへ保存し、最初のコミット前はNULLで表します。必須の状態が欠けたリポジトリは、ブランチ先端と推測せずエラーにします。

現在位置がブランチ先端以外のときに`commit`すると、変更が先端の上に積まれないよう、現在位置を起点とする新しいブランチを自動で作成して切り替え、そこへコミットします。ブランチ名は`branch-YYYYMMDD-HHMMSS`（ローカル時刻）で、既存のブランチ名やタグ名と重なる場合は末尾に`-2`、`-3`…を付けます。名前は`sprout branch OLD --rename NEW`で変更できます。`commit --json`の`created_branch`で、ブランチを自動作成したかどうかが分かります。現在位置から変更がない場合は、ブランチを作らずに`nothing to commit`となります。

## スナップショット間を移動する

`go`は、確認なしで別のスナップショットへ移動します。コミットID（または先頭部分）、ブランチ名、タグ名を指定できます。

```powershell
sprout go <commit-id>
sprout go main
```

未保存の変更がある場合は、先にその変更を移動前の現在位置の「つぼみ」として残してから移動するため、`--discard`は不要です。移動先が現在のブランチの先端ならブランチはそのまま、他のブランチの先端ならそのブランチへ切り替えます（複数のブランチの先端なら、指定したブランチ名、なければ名前順で最初のブランチ）。途中のスナップショットへの移動ではブランチを変えず、現在位置だけを移します。未追跡ファイルとの衝突やリンクがある場合は、つぼみも作らず何も変更せずに中止します。移動途中で中断された場合は、次の起動時に移動前の状態へ戻します。

`sprout move`は追跡ファイルの名前や場所を変えるコマンドで、`go`とは別のものです。

## 未保存の変更をつぼみとして残す

コミットするほどではない未保存の変更は、「つぼみ」として現在位置のスナップショットに残せます。つぼみには追跡中ファイルのその時点の内容が保存され、実体は通常のコミットと同じobjectsストアで重複排除されます。1つのスナップショットにいくつでも付けられます。

```powershell
# 未保存の変更をつぼみとして残す（作業フォルダはそのまま）
sprout bud --save

# つぼみの一覧（新しい順）
sprout bud

# つぼみに戻る
sprout bud --restore <bud-id>

# つぼみを捨てる（取り消せません）
sprout bud --drop <bud-id> --yes
```

`--restore`は、作業フォルダをつぼみを残したときの内容に戻し、現在位置をつぼみの元のスナップショットへ移します。そのとき別の未保存の変更があれば、先にそれを新しいつぼみとして残してから戻します。戻したつぼみは、書き戻しが完了した後に一覧から消えます。未追跡ファイルは削除も上書きもせず、戻す先と衝突する場合やリンクがある場合は何も変更せずに中止します。つぼみの元になっているコミットは`prune`で削除されず、つぼみが参照するオブジェクトは`gc`で削除されません。`doctor`はつぼみのオブジェクトも検査し、`stats`はつぼみの数を表示します。

## 常駐モード（serve）

GUIなどから多数のコマンドを続けて実行する場合は、`sprout serve`で1つのプロセスを常駐させ、Pythonの起動コストを省けます。標準入力へ1行1件のJSON要求を送り、標準出力から1行1件のJSON応答を受け取ります（JSON Lines、UTF-8）。

起動直後に`{"ready": true, "version": string, "protocol": 1}`を1行出力します。要求と応答の形式は次のとおりです。`args`は通常のCLI引数と同じで、`--json`を付けたコマンドは通常のCLIと同じJSONを`result`に返します。JSONではない出力は`{"text": string}`になります。`cwd`を指定すると、その要求だけそのフォルダで実行します。

```text
要求: {"id": any, "args": [string], "cwd"?: string}
成功: {"id": any, "ok": true, "exit_code": 0, "result": any}
失敗: {"id": any, "ok": false, "exit_code"?: number, "result"?: any,
       "error": {"code": string, "message": string, "details": object}}
終了: {"id": any, "command": "quit"} または標準入力のEOF
```

エラーが起きてもプロセスは終了せず、エラー応答を返して次の要求を待ちます。要求は1件ずつ順に処理し、書き込み系のコマンドは通常のCLIと同じリポジトリロックを使うため、常駐中に別プロセスのCLIを実行しても安全です。ロック中に書き込みを要求した場合は`repository_locked`エラーが返ります。`serve`の入れ子は実行できません。

## コミットからファイルを取り出す

作業フォルダや追跡状態を変えずにコミット内のファイルを書き出す場合は`export`を使います。パスを省略すると全ファイル、ファイルやディレクトリを指定すると該当するファイルだけを書き出します。相対パスの構造と更新日時はコミット時の状態が保たれます。

```powershell
sprout export <commit-id> --output ../preview
sprout export <commit-id> assets/ docs/manual.bin --output ../preview
```

出力先に同名ファイルがある場合は処理を中止します。上書きしてよい場合に限り`--force`を指定してください。

```powershell
sprout export <commit-id> assets/ --output ../preview --force
```

単一ファイルを標準出力へバイナリのまま取り出す場合は`cat`を使います。ファイルへのリダイレクトや、プレビュー用プログラムとのパイプに利用できます。

```powershell
sprout cat <commit-id> assets/image.png > old-image.png
```

## コミットのサムネイルを管理する

既存コミットにもサムネイルを後付けできます。画像を置き換えても、最初に登録した日時は維持され、更新日時だけが変わります。

```powershell
# 登録または置き換え
sprout thumbnail <commit-id> preview.webp

# メタデータを確認
sprout thumbnail <commit-id>
sprout thumbnail <commit-id> --json

# 作業ツリーを変更せず指定ファイルへ取り出す
sprout thumbnail <commit-id> --output ../preview.png

# 既存の出力ファイルを置き換える
sprout thumbnail <commit-id> --output ../preview.png --force

# 登録を削除
sprout thumbnail <commit-id> --delete
```

サムネイルの実体は通常のコミットファイルと同じobjectsストアへ保存され、同じ内容は重複して保存されません。参照中のサムネイルは`gc`で保持され、欠落や破損は`doctor`で検出されます。`--output`は追跡中の作業ファイルや`.sprout`内を上書きしません。

## コミットメッセージを変更する

```powershell
sprout message <commit-id> "クライアント確認後の最終案"
```

コミットID、親子関係、保存ファイル、添付、ブランチ、タグを変更せず、指定したコミットのメッセージだけを置き換えます。コミットIDのほか、コミットIDの一意な接頭辞、ブランチ、タグも指定できます。空のメッセージは登録できません。

## コミットのメモとラベルを管理する

コミットのスナップショットやタグを変更せず、後から編集できるメモを1件、ラベルを複数付けられます。

```powershell
# メモの設定・確認・削除
sprout note <commit-id> "クライアント確認済み"
sprout note <commit-id>
sprout note <commit-id> --delete

# ラベルの追加・一覧・削除
sprout label <commit-id> submitted
sprout label <commit-id>
sprout label <commit-id> --delete submitted

# ラベルで履歴を絞り込む
sprout log --label submitted
```

メモは前後の空白を除去して保存し、空文字を指定すると削除します。上限は20,000文字です。ラベルも前後の空白を除去し、Unicode NFCで正規化します。ラベルは1件64文字以内、1コミット32件以内で、大文字小文字を区別します。同じラベルの再追加は1件のままです。メモとラベルは`show`と`log`の通常表示およびJSON出力にも含まれます。

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

現在のリポジトリ形式はSchema Version 1です。正式リリースに向けて、現行のテーブル構成を新しい初期形式に統合しました。コミット履歴、添付、メモ、ラベル、リポジトリ固有ID・作成日時を保存し、オブジェクトはZstandardで圧縮します。ブランチは名前と独立した不変のIDで識別し、現在のブランチとコミットは専用のrepository_stateテーブルへ外部キー付きで保存します。

今回の初期仕様見直し前に作成したVersion 1、および開発中に作成した旧Version 1・2・3のリポジトリとの互換性はありません。旧Version 1は同じ番号でも構造が異なるため読み込めません。旧形式や必須構造の欠落を検出した場合は、データを自動変換・修復せずエラーにします。つぼみと状態テーブルも必須構造として検査し、起動時に不足テーブルを追加することはありません。

既存の開発用リポジトリを使い直す場合は、Sproutを終了し、必要な作業ファイルを確認したうえで`.sprout`全体をプロジェクト外へ退避し、`sprout init`で再初期化してください。作業ファイルは残りますが、以前の履歴・追跡設定・つぼみ・添付・メモ・ラベルは新しいリポジトリへ引き継がれません。必要なファイルを改めて`sprout track`し、最初のコミットを作成します。

復元途中の記録もVersion 1に統一しています。現行形式の中断処理は自動復旧しますが、番号のない旧形式や非対応バージョンの記録は変換せず拒否し、作業ファイルと復旧用バックアップを保持します。

ブランチの名前を変えてもIDは変わりません。削除済みの枝の識別情報とコミット・つぼみの作成時の名前は履歴用に保持し、同名で枝を作り直すと新しいIDになります。削除済みの枝は通常のブランチ一覧とpruneの先端保護から外れます。その枝のつぼみを戻すときは現在の有効なブランチを維持し、同名で作り直した別の枝へは接続しません。

添付は不変のIDと表示順positionを持ち、保存層は1コミットに複数のpreviewを保持できます。thumbnailは従来どおり1件に限り、置き換えても添付IDと最初の登録日時を維持します。複数previewの追加・個別操作・並べ替えコマンドは後続のTASK-38で実装します。現段階でもshowとtreeのJSONから保存された添付一覧を取得できます。

保存したオブジェクトはobjectsテーブルにも登録され、内容のSHA-256、元サイズ、圧縮後の保存サイズ、保存形式（現在はzstdのみ）、登録日時を持ちます。コミットのファイル、添付、つぼみのファイルはobjectsを外部キーで参照するため、未登録の内容を参照する行は保存できません。オブジェクトのファイルを書き込んだ後に登録が失敗・中断した場合は、どこからも参照されない未登録ファイルだけが残り、`doctor`が報告し`gc`が回収します。

通常の読み出しと保存済み内容の再利用ではobjects.encodingを確認し、非対応形式なら対象のハッシュとencodingを含むエラーで拒否します。`doctor`でも診断できます。将来の圧縮方式や保存形式の追加は、DBのSchema Versionが変わらない場合でも、旧CLIで安全に読み書きできるかを別途判断します。

復元・書き出し時のファイル更新日時は、その内容が初めてファイルとしてコミットされたときの日時をobjectsに1件だけ保持し、同じ内容のファイルにはすべてこの日時を使います。つぼみのファイルは保存時点の更新日時を個別に保持します。

コミットとつぼみには作成順を表す連番を持たせ、tree・つぼみ一覧・pruneの並び順は日時ではなくこの連番で決めます。時計の巻き戻りや同時刻の作成、SQLiteの`VACUUM`後も順序は変わりません。保存する日時はすべて`2026-10-29T01:02:03.123456+00:00`のようなマイクロ秒精度のUTC形式に統一し、DBの制約でも検査します。

作業ツリーの判定キャッシュは、履歴DBとは独立した`.sprout/worktree-cache.db`に保存します。キャッシュは任意の再生成可能な補助情報で、欠落・破損・非対応形式なら必要時に作り直し、書き込みできない場合は利用せず通常のハッシュ計算を続けます。履歴DBの再初期化は不要です。追跡解除・移動・復元などでは古い記録を破棄し、履歴DBの更新でも保守的に全記録を失効させます。開発用の旧キャッシュは移行しません。キャッシュを使ったハッシュ計算の省略は後続のTASK-56で実装します。

## コマンド一覧

| コマンド | 説明 |
| --- | --- |
| `init [PATH] [--json]` | Sproutの管理情報を作成する |
| `track PATH... [--json]` | ファイルを追跡対象へ登録する |
| `untrack PATH... [--json]` | ファイルの追跡をやめる |
| `move OLD NEW` | 追跡済みファイルを移動する |
| `status [--json]` | 現在の変更や追跡状態を確認する |
| `commit -m MESSAGE [--thumbnail IMAGE] [--json]` | 現在の状態をコミットし、必要に応じてサムネイルを登録する |
| `message COMMIT TEXT [--json]` | コミットIDや保存内容を変えずにコミットメッセージを変更する |
| `log [PATH] [-n COUNT] [--label LABEL] [--oneline\|--json]` | 現在のブランチの履歴を表示する。パス、ラベル、件数、表示形式を指定できる |
| `tree [--json]` | 削除済みブランチ由来を含むリポジトリ全体のコミットグラフを表示する |
| `diff [COMMIT_A] [COMMIT_B]` | コミット間、または作業ツリーとのファイル差分を表示する |
| `show COMMIT [--json]` | コミットの詳細を表示する |
| `thumbnail COMMIT [IMAGE] [--delete\|--output FILE] [--json]` | サムネイルの確認・登録・削除・取り出しを行う |
| `note COMMIT [TEXT] [--delete] [--json]` | コミットのメモを確認・設定・削除する |
| `label COMMIT [LABEL] [--delete LABEL] [--json]` | コミットのラベルを一覧・追加・削除する |
| `branch [NAME] [START_POINT] [--switch] [--rename NEW] [--delete NAME] [--json]` | ブランチの一覧・作成・リネーム・削除を行う。START_POINTはコミット・ブランチ・タグ。`--switch`で作成後に切り替える |
| `tag [NAME] [COMMIT] [--set-comment TEXT] [--delete NAME] [--json]` | タグの一覧・作成・コメント変更・削除を行う |
| `switch BRANCH [--json]` | 別のブランチへ切り替える |
| `serve` | JSON Linesで要求を受け付ける常駐モードを起動する |
| `go TARGET [--json]` | 未保存の変更をつぼみに残して、指定したスナップショットへ移動する |
| `bud [--save\|--restore BUD\|--drop BUD --yes] [--json]` | 未保存の変更のつぼみを一覧・保存・復元・破棄する |
| `restore COMMIT [PATH...] [--json]` | 指定したコミットを復元する。パスを指定するとそのファイルだけ復元する |
| `export COMMIT [PATH...] --output DIR [--force] [--json]` | 作業フォルダを変えずにコミット内のファイルを書き出す |
| `cat COMMIT PATH` | コミット内の単一ファイルをバイナリ標準出力へ書き出す |
| `prune START_TAG END_TAG [--dry-run] [--yes] [--json]` | タグ間のタグなし中間コミットを削除し、残存履歴を再接続する |
| `prune --all [--dry-run] [--yes] [--json]` | タグ付きコミットと現存ブランチ先端以外を全履歴から削除する |
| `gc [--dry-run]` | どのコミットからも参照されないオブジェクトを削除する |
| `doctor` | リポジトリの整合性（欠落・破損オブジェクトなど）を検査する |
| `stats` | リポジトリの件数・容量と重複排除による節約量を表示する |

コミットの指定には、完全なコミットID、一意に識別できるIDの先頭部分、ブランチ名、またはタグ名を使用できます。

`gc`は参照されないオブジェクトと、中断などで残った一時ファイル(`object-*`)を削除します。削除前に対象だけ確認したい場合は`--dry-run`を使います。

リポジトリの健全性だけ確認したい場合は`doctor`を使います。登録・参照されているオブジェクトの欠落・内容破損・サイズ不一致・非対応の保存形式、objectsに未登録のオブジェクトファイル、中断中の操作記録、残った一時ファイル、存在しないコミットを指す現在位置を報告します。問題がなければ`OK`を表示し、問題があれば終了コード1で終了します。作業ツリーや追跡状態は変更しません。

容量と重複排除の効果を確認したい場合は`stats`を使います。objectsテーブルに登録されたオブジェクトの件数・保存サイズの合計、コミット数、追跡パス数に加え、コミット上の論理サイズと実ユニークサイズの差（`Dedup saved`）を表示します。読み取り専用です。

## JSON出力

GUIから利用する`init`、`status`、`track`、`untrack`、`commit`、`message`、`log`、`tree`、`show`、`thumbnail`、`note`、`label`、`branch`、`tag`、`switch`、`restore`、`go`、`bud`と、履歴管理用の`prune`は、コマンド単位の`--json`に対応しています。成功時はstdoutへ人間向けの装飾を含まないJSONを1つだけ出力し、stderrには何も出力しません。日本語のパスやメッセージは`\u`形式へエスケープせず、そのまま出力します。

```powershell
sprout status --tracked --untracked --json
sprout log -n 5 --json
sprout tree --json
sprout prune first-draft submitted --dry-run --json
sprout show <commit-id> --json
sprout branch --json
sprout commit -m "first" --json
sprout switch ideas --json
```

更新系コマンドの成功スキーマは次のとおりです。`thumbnail`の確認と登録は添付情報、削除は添付情報に`deleted: true`を加えたオブジェクト、`--output`は`{"output": string}`を返します。`message`は変更対象と保存後のメッセージ、`note`と`label`は操作後の注釈全体を返します。`branch`の一覧は後述の配列、作成はブランチ情報、リネームは`id`・`name`・`previous_name`、削除は`id`・`name`・`deleted`、コメント更新は`id`・`name`・`comment`を返します。`id`は対象ブランチの不変のIDで、名前変更・削除・同名での再作成後も`tree`の`branch_id`と照合できます。`commit`・`switch`・`go`・`status`の`branch_id`は保存先または現在のブランチのIDです。`tag`の作成とコメント変更はタグ情報、削除は`name`と`deleted`、一覧はタグ情報の配列を返します。

```text
init:       {"root": string}
track:      {"paths": [string]}
untrack:    {"paths": [string]}
commit:     {"id": string, "branch": string, "branch_id": string, "created_branch": boolean, "message": string, "removed_paths": [string]}
message:    {"commit_id": string, "message": string}
note/label: {"commit_id": string, "note": string | null, "note_updated_at": string | null, "labels": [string]}
switch:     {"branch": string, "branch_id": string, "commit_id": string | null}
tag:        {"name": string, "commit_id": string, "comment": string, "created_at": string}
tag --delete: {"name": string, "deleted": true}
export:     {"commit_id": string, "output": string, "paths": [string]}
restore:    {"commit_id": string, "paths": [string] | null}

prune:
{
  "mode": "between" | "all",
  "dry_run": boolean,
  "start_tag": string | null,
  "end_tag": string | null,
  "removed_commits": [{"id": string, "created_at": string, "message": string}],
  "reclaimable_objects": [string],
  "reclaimable_bytes": number
}
```

読み取り系コマンドのスキーマは次のとおりです。`tracked`と`untracked`は、対応するオプションを指定した場合だけ`status`へ含まれます。`status PATH --json`では`changes`の代わりに`paths`が返ります。`current_commit`は作業ツリーの現在位置のコミットID（コミットがないときは`null`）、`at_branch_tip`はそれが現在のブランチ先端かどうかです。

```text
status:
{
  "branch": string,
  "branch_id": string,
  "current_commit": string | null,
  "at_branch_tip": boolean,
  "changes": [{"state": string, "path": string}],
  "tracked"?: [string],
  "untracked"?: [string]
}

status PATH:
{
  "branch": string,
  "branch_id": string,
  "current_commit": string | null,
  "at_branch_tip": boolean,
  "paths": [{"path": string, "tracked": boolean}]
}

log:
[{
  "id": string,
  "parent_id": string | null,
  "created_at": string,
  "message": string,
  "note": string | null,
  "note_updated_at": string | null,
  "labels": [string]
}]

tree:
{
  "current_commit": string | null,
  "at_branch_tip": boolean,
  "commits": [{
    "id": string,
    "parent_id": string | null,
    "branch_id": string,
    "branch_name": string,
    "created_at": string,
    "message": string,
    "attachments": [{
      "id": string,
      "position": number,
      "commit_id": string,
      "role": string,
      "original_name": string,
      "media_type": string,
      "object_hash": string,
      "size": number,
      "created_at": string,
      "updated_at": string
    }],
    "note": string | null,
    "note_updated_at": string | null,
    "labels": [string]
  }],
  "branches": [{
    "id": string,
    "name": string,
    "commit_id": string | null,
    "comment": string,
    "current": boolean
  }],
  "tags": [{
    "name": string,
    "commit_id": string,
    "comment": string,
    "created_at": string
  }],
  "buds": [Bud]
}

bud --json（一覧）:
[Bud]

bud --save --json / bud --drop BUD --yes --json:
Bud

go --json:
{
  "current_commit": string,
  "branch": string,
  "branch_id": string,
  "at_branch_tip": boolean,
  "bud": Bud | null,
  "changes": [{"state": string, "path": string}]
}

bud --restore BUD --json:
{
  "restored": Bud,
  "saved": Bud | null
}

Bud:
{
  "id": string,
  "base_commit_id": string | null,
  "branch_id": string,
  "branch_name": string,
  "created_at": string,
  "changes": [{"state": string, "path": string}],
  "files": [{
    "path": string,
    "object_hash": string,
    "size": number,
    "mtime_ns": number
  }]
}

show:
{
  "id": string,
  "parent_id": string | null,
  "branch_id": string,
  "branch_name": string,
  "created_at": string,
  "message": string,
  "note": string | null,
  "note_updated_at": string | null,
  "labels": [string],
  "attachments": [Attachment],
  "thumbnail": {
    "commit_id": string,
    "id": string,
    "position": number,
    "role": "thumbnail",
    "original_name": string,
    "media_type": "image/png" | "image/jpeg" | "image/webp",
    "object_hash": string,
    "size": number,
    "created_at": string,
    "updated_at": string
  } | null,
  "files": [{
    "path": string,
    "object_hash": string,
    "size": number,
    "mtime_ns": number
  }]
}

branch:
[{
  "id": string,
  "name": string,
  "commit_id": string | null,
  "comment": string,
  "current": boolean
}]
```

showとtreeの添付一覧はrole、position、添付IDの順で返します。同じrole内ではpositionが表示順です。Attachmentはid、commit_id、role、position、original_name、media_type、object_hash、size、created_at、updated_atを持ちます。roleとmedia_typeは未知の値も許可します。ブランチ一覧のid、およびコミット・つぼみのbranch_idは不変のブランチIDです。branch_nameは作成時の名前です。

JSONの日時は保存されているUTC表現、`mtime_ns`はナノ秒整数のまま返します。そのため、`show --json`と`--timezone`は同時指定できません。`log --json`と`--oneline`も表示形式が競合するため同時指定できません。

JSONモードで期待されるエラーが起きた場合は、非0で終了し、stdoutを空のまま保ってstderrへ次のJSONを1つ出力します。

```json
{"code":"uncommitted_changes","message":"working tree has uncommitted changes (use --discard to replace them)","details":{"can_discard":true}}
```

復元パスの安全性エラーは`unsafe_restore_path`、部分復元の選択範囲との衝突は`restore_scope_conflict`、復旧中に検出したファイルの衝突は`restore_recovery_conflict`を返します。これらの`details`には`path`と`reason`を含めます。

エラーは常に`code`、`message`、`details`を持ちます。代表的な`code`は、一般的な操作エラーの`sprout_error`、他の操作がロック中の`repository_locked`、未コミット変更がある`uncommitted_changes`、OSまたはSQLite操作の`repository_error`、引数指定の`usage_error`です。`repository_locked`の`details.retryable`と`uncommitted_changes`の`details.can_discard`をGUIの再試行・確認フローに利用できます。

正式リリース前は、保存形式・CLI・JSON出力の後方互換性を保証しません。GUIとCLIは同じリビジョンの組み合わせで使用してください。今回の保存形式の整理では、名前によるCLI操作は維持し、JSON出力にはブランチID・添付ID・表示順・showの添付一覧を追加しています。

## 無視パターン (`.sproutignore`)

プロジェクトルートの`.sproutignore`に、追跡したくないファイルのパターンを書けます。書式は次のとおりです。

- 1行に1パターン
- `#` で始まる行はコメント
- `*` などの glob はパス全体とファイル名の両方に照合する（例: `*.tmp`、`Thumbs.db`）
- 末尾が `/` のパターンはディレクトリとその配下を除外する（例: `cache/`）

適用されるのは次の操作だけです。

- ディレクトリを指定した `track`（配下を走査するとき）
- `status --untracked` の一覧

ファイルを明示して `track` した場合は、無視パターンより優先して登録されます。すでに追跡中のファイルの変更検出（`status` の added / modified / deleted）には影響しません。`.sproutignore` 自体も通常のファイルとして追跡できます。

## 現在の制限

最初のリリースでは、リモート同期とマージには対応していません。
大きなファイルを頻繁に更新すると、`.sprout/objects`の使用量は増えますが、不要になったオブジェクトは`gc`で削除できます。

## テスト

```powershell
uv run pytest
```

## ライセンス

Sproutは[MIT License](LICENSE)のもとで公開されています。
