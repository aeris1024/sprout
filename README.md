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

### まとめてインストール（Windows）

リポジトリのルートにある`install.cmd`をダブルクリックすると、CLIのインストール、GUIのビルド、GUIのインストールをまとめて行います。ターミナルからは次のコマンドでも実行できます。

```powershell
.\install.cmd
```

[uv](https://docs.astral.sh/uv/)、Node.js 20.19以降、pnpm、Rust stable（MSVC）、Visual Studio 2022のC++ビルドツールが必要です。足りないツールがある場合は、導入方法を表示して中止します。GUIはユーザー単位でインストールされるため、管理者権限は不要です。GUIの初回ビルドには数分かかります。

再実行すると、現在のコードでCLIとGUIを更新します。GUIを起動中の場合は終了してから実行してください。次のオプションも使えます。

```powershell
# CLIだけをインストールする（Node.jsやRustは不要）
.\install.cmd -CliOnly

# GUIはインストールせず、インストーラーの作成までにする
.\install.cmd -BuildOnly
```

CLIのインストール先がPATHにない場合は警告が出ます。`uv tool update-shell`を実行してターミナルを開き直してください。

### 個別にインストール

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

`gui/`にはTauri 2 + React + TypeScript + Viteで構築したWindows向けGUIがあります。GUIはSproutの管理データへ直接触れず、PATHまたは設定画面で指定したCLIを`--json`付きで呼び出します。インストールは前述の`install.cmd`でまとめて行えます。開発中は次のコマンドで起動します。

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
sprout file track document.bin references
sprout status
```

作業の区切りでコミットを作成します。

```powershell
sprout leaf create -m "最初のスナップショット"
```

コミットへ小さな静止画像を付ける場合は`--thumbnail`を指定します。PNG、JPEG、WebPに対応し、ファイルサイズは2 MiB以下、幅と高さはそれぞれ4096ピクセル以下に制限されます。画像は実際の内容をデコードして検証され、破損画像、アニメーション画像、拡張子だけを変更した非画像ファイルは拒否されます。

```powershell
sprout leaf create -m "色を調整" --thumbnail preview.png
```

保存した履歴は、次のコマンドで確認できます。

```powershell
sprout leaf list
sprout leaf list scene.blend
sprout leaf show <commit-id>
sprout leaf tree
```

`sprout leaf list`は現在のブランチの履歴を表示します。パスを指定すると、そのパスの内容が変わった葉だけを表示し、内容が同じままの葉は省きます。一度も登場していないパスでは`No history for path:`と表示されます。
表示件数は`-n/--max-count`で制限でき、`--oneline`を指定すると各コミットを1行で表示できます。

```powershell
sprout leaf list -n 5
sprout leaf list --oneline
sprout leaf list scene.blend -n 5 --oneline
sprout leaf list --label submitted
sprout leaf list --file-id <file-id> --json
```

`--label`は前後の空白とUnicode表現を正規化したうえで、ラベルの大文字小文字を区別して完全一致検索します。パス、件数、表示形式の指定とも併用できます。

`--file-id`では全ブランチの同一素材の保存記録を表示します。内容不変の保存、改名・移動、削除済みブランチ由来の葉も含み、各時点のパス・内容・更新日時を新しい順に返します。`-n/--max-count`、`--oneline`、`--json`を利用できます。検索範囲が異なるため、PATHや`--label`との同時指定は拒否します。JSONは既存の素材履歴と同じ`commit_id`・`path`・`file_id`等を持つ配列で、通常モードの`id`・メモ・ラベルを持つ配列とは区別します。`log`は同じ処理への手打ち用aliasです。

`sprout leaf show`のコミット日時とファイル更新日時は、既定ではUTCで表示されます。ローカルタイム、またはIANAタイムゾーン名を指定することもできます。

```powershell
sprout leaf show <commit-id> --timezone local
sprout leaf show <commit-id> --timezone Asia/Tokyo
```

### サンプルリポジトリで試す

ブランチ、タグ、サムネイル、preview、つぼみ、ゴミ箱などが入ったサンプルを生成できます。Sproutのリポジトリで、存在しないフォルダか空のフォルダを指定して実行します。

```powershell
uv run python scripts/create_sample_repo.py ../sprout-sample
```

生成先の`GUIDE.md`に、CLIとGUIで試す手順があります。

## ブランチを使う

現在のブランチ先端から別案を作る場合は、ブランチを作成して移動します。起点を省略できるのは最初の葉を保存した後です。

```powershell
sprout branch create experiment --comment="別の方法を試す"
sprout go --branch experiment

# 過去の葉を起点に、作成と移動をまとめて行う
sprout branch create rethink <leaf-id> --switch
sprout branch create from-tag submitted --switch

# 一覧、名前・コメントの変更、削除
sprout branch list
sprout branch list --deleted
sprout branch rename experiment prototype
sprout branch comment prototype "試作版"
sprout branch delete prototype
```

起点には葉ID、一意な接頭辞、ブランチ名、タグ名を指定できます。起点を省略すると現在のブランチ先端から作成します。ただし、現在位置が途中の葉にある場合は、誤った分岐を防ぐため`--switch`の有無にかかわらず起点の省略を拒否します。途中の葉から分岐する場合は葉を明示してください。

`--switch`を付けなければブランチを作るだけです。付けると作成後に移動し、未保存の追跡変更は既定でつぼみに残します。変更がある場合の拒否には`--reject-changes`、ゴミ箱へ保存したうえでの破棄には`--discard`を指定します。現在のブランチは削除できません。名前を変更してもブランチのIDと現在の選択を保ちます。

## タグを使う

保存した葉に動かない目印を付ける場合はタグを使います。葉を省略すると現在のブランチ先端へ作成します。

```powershell
sprout leaf tag create submitted --comment="提出版"
sprout leaf tag create first-draft <leaf-id> --comment="初稿"
sprout leaf tag comment first-draft "初稿（差し戻し前）"
sprout leaf tag list
sprout leaf tag delete first-draft
sprout leaf show submitted
sprout go submitted
```

コメントは空文字で解除できます。タグは葉の参照として使え、タグ付きの葉は単一削除や間引きから保護されます。タグ自体の削除は葉を削除せず、ゴミ箱から戻せます。

## リポジトリ全体の履歴を見る

`leaf list`は現在のブランチだけをたどります。分岐した履歴や、削除済みブランチから作られたコミットを含む全履歴を見る場合は`leaf tree`を使います。

```powershell
sprout leaf tree
```

人間向け表示は古いコミットから新しいコミットへ親子関係をASCII枝で示します。`created`はコミット作成時のブランチ名、`branch`と`tag`は現在そのコミットを指す参照です。現在のブランチには`*`が付きます。サムネイル、previewの件数、メモ、ラベルもマーカーで確認できます。

```text
* a12bc34de567 initial [created:main] [tag:baseline]
|- * b23cd45ef678 main work [created:main] [branch:*main]
`- * c34de56fa789 side work [created:side] [thumbnail] [previews:2] [note] [labels:Candidate]
```

削除したブランチ名は現在の`branch`参照から消えますが、そのブランチで作成したコミットと`created`の値は保持されます。GUIや外部ツールから利用する場合は`leaf tree --json`で平坦なコミット配列と現在の参照を取得できます。人間向けツリーは古い順、JSONの`commits`配列は新しい順です。

## 履歴を間引く

制作途中のタグなしコミットを削除する場合は`leaf prune`を使います。2つのタグを古い順に指定するタグ間モードでは、その祖先経路内にあるタグなし中間コミットだけが対象です。すべてのタグ付きコミット、現在存在する各ブランチの先端、作業ツリーの現在位置のコミットは常に保護されます。

```powershell
# 変更せずに削除対象と、gcで回収可能になる容量を確認
sprout leaf prune first-draft submitted --dry-run

# 確認したタグ間を実際に間引く
sprout leaf prune first-draft submitted --yes
```

全履歴モードは、タグ付きコミットと現存ブランチ先端以外をすべて削除します。削除済みブランチ由来で、タグも現存ブランチ参照もないコミットも対象になります。

```powershell
sprout leaf prune --all --dry-run
sprout leaf prune --all --yes
```

`leaf prune`は取り消せません。実行には`--yes`が必要で、削除後は残したコミットの親が元の履歴上で最も近い残存祖先へ接続されます。部分復元などで作業ツリーの内容が削除対象の過去コミットと一致する場合は、そのコミットへタグを付けるかブランチを作成するまで実行を拒否します。コミット削除だけではobjectsのファイルやSQLiteデータベース自体のサイズは縮まらないため、表示された容量を実際に回収するには続けて`sprout maintenance gc`を実行してください。SQLiteの`VACUUM`は行いません。

## 葉を1枚だけ削除する

失敗した保存や不要になった1枚のコミットだけを消す場合は`delete-commit`を使います。コミットID・接頭辞・ブランチ名・タグ名で指定できますが、タグ付きのコミットは削除できません（先にタグを外してください）。

```powershell
# 変更せずに影響（移るブランチ・いまここ・つなぎ直す子・付け替えるつぼみ）と回収可能な容量を確認
sprout leaf delete 3f2a9c1b --dry-run

# 確認した内容で削除する
sprout leaf delete 3f2a9c1b --yes
```

削除するコミットを指していた参照は、すべてその親へ移します。

- 同じコミットを先端とするすべてのブランチと「いまここ」は親へ移ります。作業ファイルは変更しないため、削除したスナップショットとの差分は未保存の変更として残ります。
- 子のコミットは親へつなぎ直します。ルートのコミットを削除すると子がルートになり、親がない場合はブランチと現在位置がコミットなしになります。
- そのコミットを起点にしたつぼみは、内容を変えず起点を親へ付け替えます。
- そのコミットのファイル一覧・添付・メモ・ラベルは削除されます。他のコミットの内容は変わりません。

`delete-commit`は参照を移すため、実行には`--yes`が必要です。削除内容はゴミ箱へ保持し、参照が変更される前なら復旧できます。`--dry-run`は何も変更せず、実際の削除と同じ影響を報告します。途中で失敗した場合は削除内容と復旧記録の両方をロールバックします。ゴミ箱の実体は`maintenance gc`から保護されます。`reclaimable_objects`・`reclaimable_bytes`は、その葉だけが参照する内容のうち、他のつぼみやゴミ箱にも保護されていない分です。削除直後に回収できる容量ではありません。

### ゴミ箱から復旧する

単一の葉の削除、previewの削除、previewの置き換え前の版、捨てたつぼみ、`--discard`で破棄した未保存の変更、削除したメモ・タグ・ブランチは、通常の履歴・添付一覧とは別にゴミ箱へ保存します。再起動後も残り、自動削除や保持期限はありません。作成順の新しい項目から一覧し、時計の巻き戻りやVACUUMでも順序を維持します。復旧した項目はゴミ箱から取り除きます。不要になった復旧データは手動で完全削除してください。

```powershell
sprout trash list
sprout trash show <trash-id> --json
sprout trash restore <trash-id> --dry-run --json
sprout trash restore <trash-id>

# 対象と容量を確認してから完全削除する
sprout trash purge <trash-id> --dry-run --json
sprout trash purge <trash-id> --yes
sprout maintenance gc
```

復旧IDは一覧の完全なIDを指定します。葉の復旧では、保存ファイル・添付・メモ・ラベルに加え、削除時に変えた子の親・ブランチ先端・現在位置・つぼみの起点を戻します。作業ファイルや追跡設定は変更しません。削除後に影響範囲の記録が編集・削除された場合や、必要な親が失われた場合、ID・連番が衝突する場合は、`trash_restore_conflict`で全体を拒否し、ゴミ箱も残します。後から進めた履歴や同名の別ブランチを上書きしません。

削除したメモ（`note_delete`）は内容と更新日時を、タグ（`tag_delete`）は対象の葉とコメントを、ブランチ（`branch_delete`）は枝先・コメント・IDを含めて戻します。対象の葉が失われている場合、その葉に新しいメモがある場合、同じ名前のブランチやタグがすでにある場合は、理由を示して`trash_restore_conflict`で拒否します。メモの内容を別の内容へ上書きした場合はゴミ箱に残りません。

捨てたつぼみ（`bud_delete`）と破棄した未保存の変更（`discard`）は、ファイルの内容・素材ID・名前ごと保存し、復旧すると「つぼみ」として戻ります。作業ファイルは変更しないので、内容へ戻すには`bud restore`を使います。`--discard`では実行時点の追跡ファイル全体を保存します（部分復元でも同じです）。戻す変更がなければ項目を作らず、復元が失敗した場合は項目を取り消します。つぼみの起点の葉が失われている場合は`trash_restore_conflict`で拒否します。

previewは削除・置き換え前の添付ID・内容・元ファイル名・形式・サイズ・表示順・作成日時・更新日時をそのまま戻します。対象コミットが存在し、そのpreview一覧が記録した操作直後の状態と一致することが必要です。複数回置き換えた場合は新しい復旧項目から順に戻してください。追加・並べ替え・他のpreviewの編集などで一覧が変わった場合も拒否します。

各項目の`protected_bytes`はその項目が保護するオブジェクトの圧縮後容量で、通常の履歴や他のゴミ箱と共有する分も含みます。項目間で単純に足すと重複します。`reclaimable_bytes`はその項目を完全削除した後に、他の履歴・添付・つぼみ・ゴミ箱から参照されなくなる容量です。完全削除は復旧記録だけを破棄し、実体は次回の`maintenance gc`が回収します。完全削除を取り消すことはできず、過去のpreview版を順に戻す経路や、削除した葉に属するpreviewの復旧経路も失われる場合があります。

`trash list`は概要の配列、`trash show`は概要と`changes`（復旧する記録と操作直後の記録）、`trash restore`と`trash purge`は概要と`dry_run`・`restored`または`purged`をJSONで返します。`trash restore --dry-run`も競合と必要な内容の健全性を検査します。不正・非対応の復旧記録は`invalid_trash_record`で拒否し、`maintenance doctor`でも診断します。ゴミ箱の記録形式は整数のVersion 1です。

`leaf prune`は引き続き取り消し対象外ですが、ゴミ箱が保護する実体を回収対象に含めません。`leaf archive`は通常の履歴を対象とし、ゴミ箱を含めません。復旧データもバックアップする場合は、Sproutを終了して`.sprout`を含むプロジェクト全体をコピーしてください。

## 過去の状態へ戻る

作業フォルダ全体の移動には`go`を使います。葉ID、一意な接頭辞、ブランチ名、タグ名を指定できます。

```powershell
sprout go <leaf-id>
sprout go submitted
sprout go --branch main
sprout go <leaf-id> --keep-branch
sprout go --branch main --reject-changes
sprout go --branch main --discard
```

未保存の追跡変更は、既定で移動前の現在位置のつぼみに残してから移動します。`--reject-changes`は未保存変更があれば拒否し、`--discard`は置き換える変更をゴミ箱に残します。この2つは併用できません。未追跡ファイルは削除・上書きしません。

ブランチ名の指定や`--branch NAME`では、同じ先端を共有する別のブランチがあっても指定したブランチを選びます。空のブランチへも移動でき、そのとき現在位置はJSONで`null`です。葉IDやタグを指定すると、現在のブランチが移動先を先端に持つ場合はそのブランチを保ち、それ以外は移動先を先端に持つブランチの名前順で選びます。途中の葉への移動ではブランチを変えず、現在位置だけを移します。

`--keep-branch`では移動先にかかわらず現在のブランチと先端を保ちます。現在位置が先端以外の状態で`leaf create`すると、現在位置から新しいブランチを自動作成して保存します。自動名はローカル時刻の`branch-YYYYMMDD-HHMMSS`で、衝突時は連番を付けます。`leaf create --json`の`created_branch`で確認でき、`branch rename OLD NEW`で名前を変えられます。変更がなければブランチを作らず`nothing_to_commit`で拒否します。

### 差分と部分復元

```powershell
# 現在位置と作業フォルダ、指定した葉と作業フォルダ、2枚の葉の比較
sprout file diff
sprout file diff <leaf-id>
sprout file diff <leaf-a> <leaf-b>

# 指定したファイルやフォルダだけ戻す。PATHは省略できない
sprout file restore <leaf-id> docs/manual.bin
sprout file restore <leaf-id> assets/
sprout file restore <leaf-id> assets/ --discard
```

`file restore`は選択外のファイル、現在位置、ブランチ先端を変えません。対象パスに未保存変更がある場合は拒否し、`--discard`を付けた場合だけゴミ箱へ残して復元します。部分復元でも、破棄時の復旧用データは追跡ファイル全体から保存します。

未追跡ファイルや未追跡の空フォルダとの衝突、シンボリックリンク、Windowsのジャンクションがある場合は拒否します。リンク先がプロジェクト内でも`--discard`で検査を省略しません。全体移動ではファイルとフォルダ構成の変更に必要な追跡ファイルを退避し、空になったフォルダだけを除去して配置します。部分復元で選択外のファイルの移動・削除が必要な場合は中止するため、その場合は全体移動を使ってください。

移動・復元の途中で中断した場合は、次回起動時に記録済みの操作を巻き戻します。再度中断しても、復旧が完了するまで退避ファイルを保持します。復旧先にリンクや新しい衝突があれば原因のパスを表示して停止します。必要な作業ファイルを保全して原因を解消し、再実行してください。復旧完了前に`.sprout/tmp`を削除したり、復元・復旧中に別アプリでファイル構成を変更したりしないでください。

Sproutは作業フォルダの基になる葉を「現在位置」として保存します。移動、ブランチ作成後の移動、つぼみの復元、葉の保存が成功すると更新します。部分復元、失敗、中断後の巻き戻しでは更新しません。`status`、引数なしの`file diff`、未保存変更の判定は、ブランチ先端と現在位置を区別します。

## 未保存の変更をつぼみとして残す

つぼみは追跡ファイルのその時点の内容を保存し、現在位置の葉にいくつでも付けられます。内容は通常の葉と同じobjectsストアで重複排除します。

```powershell
sprout bud save --name "配色の別案"
sprout bud save --keep-files
sprout bud list
sprout bud rename <bud-id> "修正案"
sprout bud restore <bud-id>
sprout bud delete <bud-id> --yes
```

`bud save`は未保存変更をつぼみに移し、作業フォルダを現在位置の内容へ戻します。追跡中の追加ファイルもつぼみに移り、未追跡ファイルは変えません。書き戻しが失敗した場合は作業ファイルとつぼみを変更しません。`--keep-files`では作業フォルダをそのままにし、内容をつぼみへ写すため、その後に移動すると同じ内容のつぼみが増える場合があります。

`bud restore BUD`は、別の未保存変更があれば先につぼみへ退避し、指定したつぼみの内容と現在位置を戻します。**成功したつぼみは一覧から消えます。** 未追跡ファイルとの衝突やリンクがある場合は、作業ファイルと元のつぼみを保って拒否します。名前は1行256文字までで、空文字で解除できます。自動退避では名前は空です。

つぼみが参照する葉は`leaf prune`から、その内容は`maintenance gc`から保護されます。`maintenance doctor`は内容を検査し、`maintenance stats`はつぼみの数を表示します。GUIの「ブランチを作る」は`branch create NAME LEAF --switch`を使い、既定で未保存変更をつぼみに残します。

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

作業フォルダや追跡状態を変えずにコミット内のファイルを書き出す場合は`file export`を使います。パスを省略すると全ファイル、ファイルやディレクトリを指定すると該当するファイルだけを書き出します。相対パスの構造と更新日時はコミット時の状態が保たれます。

```powershell
sprout file export <commit-id> --output ../preview
sprout file export <commit-id> assets/ docs/manual.bin --output ../preview
```

出力先に同名ファイルがある場合は処理を中止します。上書きしてよい場合に限り`--force`を指定してください。

```powershell
sprout file export <commit-id> assets/ --output ../preview --force
```

単一ファイルを標準出力へバイナリのまま取り出す場合は`file cat`を使います。ファイルへのリダイレクトや、プレビュー用プログラムとのパイプに利用できます。

```powershell
sprout file cat <commit-id> assets/image.png > old-image.png
```

## 全履歴を静的アーカイブへ書き出す

Sproutを使わなくなった後も過去のファイルと履歴を参照できるよう、DBに残る全コミットを通常のファイル・HTML・JSONへ一括展開できます。現在のブランチから到達できない、削除済みブランチ由来のコミットも含みます。出力はWebブラウザとファイルマネージャーだけで閲覧でき、サーバー、CDN、JavaScript、Sprout、Pythonを必要としません。フォルダごと別の場所へコピーしても相対リンクで閲覧できます。

```powershell
# 実行前にコミット数・作成予定ファイル数・推定展開容量・出力先の空き容量を確認
sprout leaf archive --output ../sprout-archive --dry-run

# 書き出す（出力先は存在しないか空のディレクトリ）
sprout leaf archive --output ../sprout-archive
sprout leaf archive --output ../sprout-archive --json
```

出力構成は次のとおりです。

```text
sprout-archive/
  index.html      全コミットの日時・ID・メッセージ・ブランチ・タグ・メモ・ラベル・親子関係
  archive.json    リポジトリID・作成日時、全ブランチ（削除済みを含む）・タグ・コミットのメタデータ
  README.txt      アーカイブの説明
  snapshots/<UTCのコミット日時>_<短縮コミットID>/   例: 20261029T010203.123456Z_0123456789ab
    index.html    コミットの詳細、サムネイル、保存された表示順のpreview、ファイル一覧
    commit.json   archive.jsonと同じそのコミットの情報
    files/        コミット時の相対パス構造のままのファイル
    attachments/thumbnail/<添付ID>/<元ファイル名>
    attachments/previews/<表示順3桁>_<添付ID>/<元ファイル名>
```

JSONにはコミットの親ID・子ID・作成時のブランチ名とID・メモ・ラベル、ファイルのパス・サイズ・SHA-256、添付の添付ID・役割・表示順・元ファイル名・メディア種別・サイズ・SHA-256・アーカイブ内の位置を保存します。`repository_id`と`repository_created_at`により、コピー後も元のリポジトリを一意に識別できます。添付は添付IDごとのフォルダへ置くため、元ファイル名が同じpreviewも上書きされません。ファイル名に使えない文字はアーカイブ上のファイル名でだけ`_`へ置き換え、JSONとHTMLには元の名前を残します。HTMLでは画像を`img`、音声を`audio`、動画を`video`で表示・再生し、その他の形式はリンクから開けます。

`.sprout`では同じ内容を1つの圧縮オブジェクトとして共有しますが、アーカイブでは全コミットの全ファイルを非圧縮のまま個別に書き出すため、容量は「コミット数×各コミットのファイルサイズ」に近くなり、`.sprout`より大幅に増えることがあります。書き出し前に推定容量と空き容量を比較し、不足する場合は何も書かずに`archive_insufficient_space`エラーにします（`--dry-run`では終了コード1）。

既存の空でない出力先やファイルへは書き込みません。書き出しは出力先の隣の`.<出力名>.sprout-archive-incomplete`で行い、完了した時点で出力先へ名前を変えます。この作業フォルダには`SPROUT-ARCHIVE-INCOMPLETE.txt`を置くため、中断された出力を識別できます。同じ出力先で再実行すると、この目印がある作業フォルダだけを削除してやり直します。目印のない同名フォルダがある場合は削除せずエラーにします。展開中にオブジェクトの欠落・破損（SHA-256やサイズの不一致）を検出した場合は、対象のコミット、ファイルパスまたは添付IDを示す`archive_object_invalid`エラーで失敗し、作業フォルダを削除します。完成したように見えるアーカイブは残りません。

コミットのファイル更新日時は`file export`と同じく復元しますが、Sproutが保存していない空ディレクトリ、権限、所有者、シンボリックリンク、拡張属性などは再現しません。つぼみ（未コミットの変更）はアーカイブに含みません。

## コミットのサムネイルを管理する

既存コミットにもサムネイルを後付けできます。画像を置き換えても、最初に登録した日時は維持され、更新日時だけが変わります。

```powershell
# 登録または置き換え
sprout leaf thumbnail set <commit-id> preview.webp

# メタデータを確認
sprout leaf thumbnail show <commit-id>
sprout leaf thumbnail show <commit-id> --json

# 作業ツリーを変更せず指定ファイルへ取り出す
sprout leaf thumbnail export <commit-id> --output ../preview.png

# 既存の出力ファイルを置き換える
sprout leaf thumbnail export <commit-id> --output ../preview.png --force

# 登録を削除
sprout leaf thumbnail delete <commit-id>
```

葉ごとのサムネイルは、追跡対象外やプロジェクト外の対応画像も直接登録できます。サムネイル自動生成元は追跡ファイルから指定するプロジェクト単位の設定です。

サムネイルの実体は通常のコミットファイルと同じobjectsストアへ保存され、同じ内容は重複して保存されません。参照中のサムネイルは`maintenance gc`で保持され、欠落や破損は`maintenance doctor`で検出されます。`--output`は追跡中の作業ファイルや`.sprout`内を上書きしません。

### サムネイル自動生成元からサムネイルを作る

`poster.png`のような追跡中の画像をサムネイル自動生成元に指定すると、サムネイルを指定せずに保存したとき、そこから長辺512pxのサムネイルを自動で作ります。`--thumbnail`を指定した場合はそちらを優先します。

```powershell
sprout leaf thumbnail source set poster.png       # 指定する
sprout leaf thumbnail source show                 # 確認する
sprout leaf thumbnail source apply --dry-run      # 適用できる葉を確認する
sprout leaf thumbnail source apply                # 登録済みのサムネイルは変更しない
sprout leaf thumbnail source clear                # 解除する
```

指定は素材IDで保持するので、`file move`や大文字小文字の改名の後も有効です。対応形式はPNG・JPEG・静止WebP・BMPです。サムネイル自動生成元が追跡されていない、画像でない、大きすぎる、読み取れない場合も保存は成功し、サムネイルなしになります。理由は警告と、`leaf create --json`の`cover`（`applied`と`reason`）で確認できます。`status --tracked --json`には、指定中の場合だけ`cover`を含めます。指定はリポジトリの`meta`に保存します。

## コミットのpreviewを管理する

サムネイルは芽のマップへ常時表示する小さな静止画像で、1コミットに1件です。previewはコミットを選んだときに再生・表示するためのファイルで、1コミットに複数登録できます。画像、音声、動画、3Dモデル、文書、未知のバイナリなど形式は問わず、内容をそのまま保存します。media_typeはファイル名から推定し、推定できない場合は`application/octet-stream`になります。`--media-type`で明示することもできます。

```powershell
# 末尾へ追加（複数指定時はすべて追加されるか、1件も追加されない）
sprout leaf preview add <commit-id> voice.wav model.stl notes.pdf

# 保存前にサイズと容量への影響を確認
sprout leaf preview add <commit-id> movie.mp4 --dry-run

# 表示順に一覧
sprout leaf preview list <commit-id>
sprout leaf preview list <commit-id> --json

# 添付IDまたは一意な接頭辞で個別に操作
sprout leaf preview replace <commit-id> <preview-id> voice-v2.wav
sprout leaf preview export <commit-id> <preview-id> --output ../voice.wav
sprout leaf preview delete <commit-id> <preview-id>

# 表示順を変更（そのコミットのpreviewをすべて新しい順に並べる）
sprout leaf preview order <commit-id> <preview-id-3> <preview-id-1> <preview-id-2>
```

各previewは不変の添付IDで識別されます。同じファイル名でも別のpreviewとして登録でき、置き換え・並べ替え・他のpreviewの削除でIDは変わりません。置き換えでは表示順と作成日時を維持し、更新日時だけが変わります。削除すると残りのpreviewは相対順を保ったまま詰められます。表示順はDBに保存され、再オープン後も一覧・`leaf show`・`leaf tree`とそれぞれのJSONが同じ順で返します。

サムネイル向けの2 MiB・画素数の上限はpreviewへ適用しません。ただし100 MiBを超えるファイルは誤登録を防ぐため`--yes`を付けた場合だけ登録し、付けない場合は何も保存せず`preview_confirmation_required`エラーにします。`--dry-run`は各ファイルのサイズ、media_type、既に保存済みの内容か、圧縮前で最大何バイト増えるかを表示し、何も保存しません。

previewの実体は通常のファイル・サムネイルと同じobjectsストアへ保存され、同じ内容は重複して保存されません。追加・置き換え・削除・並べ替え・取り出しが失敗した場合、既存previewのデータ・ID・表示順と既存の出力先ファイルは変更されません。`file export`は追跡中の作業ファイルや`.sprout`内を上書きせず、既存の出力先は`--force`を付けた場合だけ置き換えます。GUIが表示に対応していない形式も、内容を失わずに取り出せます。

GUI向けの `sprout leaf preview image COMMIT PREVIEW_ID --json` は、選んだ静止画像を検証して表示用PNGのdata URL、原本形式（format）、元の寸法（width/height）、表示用寸法（display_width/display_height）を返します。PNG・JPEG・静止WebP・BMPを対象に、原本20 MiB・一辺8192px・1600万画素を上限とし、表示用は長辺2048px以内に縮小します。原本の内容は変更しません。

## コミットメッセージを変更する

```powershell
sprout leaf edit <commit-id> --message="クライアント確認後の最終案"
```

コミットID、親子関係、保存ファイル、添付、ブランチ、タグを変更せず、指定したコミットのメッセージだけを置き換えます。コミットIDのほか、コミットIDの一意な接頭辞、ブランチ、タグも指定できます。空のメッセージは登録できません。

## コミットのメモとラベルを管理する

コミットのスナップショットやタグを変更せず、後から編集できるメモを1件、ラベルを複数付けられます。

```powershell
# メモの設定・確認・削除
sprout leaf edit <commit-id> --note="クライアント確認済み"
sprout leaf show <commit-id>
sprout leaf edit <commit-id> --clear-note

# ラベルの追加・葉ごとの一覧・解除
sprout leaf label add <commit-id> submitted
sprout leaf label list <commit-id>
sprout leaf label remove <commit-id> submitted

# プロジェクト全体で使用中のラベルと利用中の葉数
sprout leaf label list
sprout leaf label list --json

# ラベルで履歴を絞り込む
sprout leaf list --label submitted
```

メッセージとメモは`leaf edit`で同時に指定でき、すべて成功するか、すべて拒否します。未指定の項目は変更しません。メモは前後の空白を除去して保存し、空文字または`--clear-note`で削除してゴミ箱に残します。`--note`と`--clear-note`は併用できません。上限は20,000文字です。ラベルも前後の空白を除去し、Unicode NFCで正規化します。ラベルは1件64文字以内、1コミット32件以内で、大文字小文字を区別します。同じラベルの再追加は1件のままです。メモとラベルは`leaf show`と`leaf list`の通常表示およびJSON出力にも含まれます。

`leaf label list`は全ブランチの現存する葉から使用中のラベルを集計し、名前順に表示します。削除済みブランチ由来の葉も含み、ゴミ箱にしか残っていない付与は含みません。最後の付与を外すと一覧から消え、葉を復旧すると再び集計されます。JSONは`[{"name":"submitted","leaf_count":2}]`形式です。葉を指定した一覧はその葉の付与情報を返し、`leaf list --label`による履歴の絞り込みとは用途が異なります。専用のラベル辞書は保存しません。

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

ファイルの追跡をやめる場合は`file untrack`を使用します。作業フォルダのファイル自体は削除されません。

```powershell
sprout file untrack document.bin
```

追跡済みファイルの名前や場所を変える場合は`file move`を使用します。
作業フォルダのファイルを移動し、追跡パスも更新します。

```powershell
sprout file move document.bin archive/document.bin
sprout leaf create -m "ファイルを移動"
```

`status`と`leaf create`はファイル内容で変更を判定します。
内容が同じで更新時刻だけが変わったファイルは、変更なしとして扱われます。

## データの保存場所

履歴は、初期化したフォルダ内の`.sprout`へ保存されます。バックアップや別のディスクへ移動するときは、`.sprout`を含めてフォルダ全体をコピーしてください。

`.sprout`の内容は手動で編集しないでください。処理が途中で中断された場合は、次回のSprout起動時に可能な範囲で自動的に復旧します。

現在のリポジトリ形式はSchema Version 1です。コミット履歴、添付、メモ、ラベル、リポジトリ固有ID・作成日時を保存し、オブジェクトはZstandardで圧縮します。ブランチは名前と独立した不変のIDで識別し、現在のブランチとコミットは専用のrepository_stateテーブルへ外部キー付きで保存します。

保存構造は`src/sprout/repository.py`の`SCHEMA`で定義しています。起動時に形式番号、必須テーブル・列・索引・制約と参照整合性を検査します。不正な構造や対応していない番号の場合は、データを変更せずエラーを返します。

ブランチには作成日時と削除日時を保存します。削除日時は`sprout branch list --deleted`で一覧でき、`branch list --json`・`leaf tree --json`にも含めます（`leaf tree --json`は`deleted_branches`）。名前を変えても作成日時は変わりません。

ブランチの名前を変えてもIDは変わりません。削除済みの枝の識別情報とコミット・つぼみの作成時の名前は履歴用に保持し、同名で枝を作り直すと新しいIDになります。削除済みの枝は通常のブランチ一覧とpruneの先端保護から外れます。その枝のつぼみを戻すときは現在の有効なブランチを維持し、同名で作り直した別の枝へは接続しません。

添付は不変のIDと表示順positionを持ち、1コミットに複数のpreviewを保持できます。thumbnailは従来どおり1件に限り、置き換えても添付IDと最初の登録日時を維持します。previewは`sprout leaf preview`で追加・個別操作・並べ替えでき、showとtreeのJSONからも保存された添付一覧を取得できます。

保存したオブジェクトはobjectsテーブルにも登録され、内容のSHA-256、元サイズ、圧縮後の保存サイズ、保存形式（現在はzstdのみ）、登録日時を持ちます。コミットのファイル、添付、つぼみのファイルはobjectsを外部キーで参照するため、未登録の内容を参照する行は保存できません。オブジェクトのファイルを書き込んだ後に登録が失敗・中断した場合は、どこからも参照されない未登録ファイルだけが残り、`maintenance doctor`が報告し`maintenance gc`が回収します。

通常の読み出しと保存済み内容の再利用ではobjects.encodingを確認し、非対応形式なら対象のハッシュとencodingを含むエラーで拒否します。`maintenance doctor`でも診断できます。

ファイル更新日時は、コミットごとの各パスに`commit_files.mtime_ns`として保存します。同じ内容の別ファイルや別コミットでも日時を共有せず、その保存時点の値を全体移動・部分復元・ブランチ作成後の移動・`file export`・`leaf archive`で使います。つぼみも引き続き各パスの日時を保持します。objectsは内容のSHA-256による重複排除を担当し、更新日時を持ちません。

更新日時だけの変化は`status`・`file diff`・パス指定の`leaf list`で変更とせず、`leaf create`やつぼみ保存も日時だけでは作成しません。内容やパスが変わって保存が成立したときには、内容の変わらないファイルも含め、全パスの実際の日時を記録します。日時の差だけで未保存変更の警告や復元拒否を起こすことはありません。

`mtime_ns`は符号付き64ビットのナノ秒整数で、NULLや整数以外の保存値を拒否します。Unix epochの0や、それ以前を表す負の整数も有効です。制約を無効にして壊した値は読み出し時に拒否し、`maintenance doctor`でも検出します。保存値はファイルシステムから読み取った精度のまま保持し、復元先の時刻精度に応じて丸められる場合があります。丸められた日時だけを理由に未保存変更とは判定しません。

コミットとつぼみには作成順を表す連番を持たせ、tree・つぼみ一覧・pruneの並び順は日時ではなくこの連番で決めます。時計の巻き戻りや同時刻の作成、SQLiteの`VACUUM`後も順序は変わりません。連番は`id_sequences`テーブルで採番し、コミット・つぼみ・ゴミ箱項目を削除しても同じ番号を再利用しないため、ゴミ箱から戻した葉は元の順序に戻ります。カウンターの不足は起動時に、既存の番号より小さいカウンターは`maintenance doctor`が`invalid_sequence`として検出します。コミット・つぼみ・添付などの作成日時や更新日時は`2026-10-29T01:02:03.123456+00:00`のようなマイクロ秒精度のUTC形式に統一し、DBの制約でも検査します。

作業ツリーの判定キャッシュは、履歴DBとは独立した`.sprout/worktree-cache.db`に保存します。キャッシュは任意の再生成可能な補助情報で、欠落・破損・非対応形式なら必要時に作り直し、書き込みできない場合は利用せず通常のハッシュ計算を続けます。履歴DBの再初期化は不要です。追跡解除・移動・復元などでは古い記録を破棄し、履歴DBの更新でも保守的に全記録を失効させます。

`status`、`file diff`、未保存の変更の判定（`go`・`file restore`・`bud restore`・`leaf prune`）は、このキャッシュを使って変更のないファイルのハッシュ計算を省略します。前回計算したときとサイズ、更新日時、作成・変更日時、ファイルの識別子（デバイスとinode／ファイルインデックス）がすべて一致し、かつ記録時点で更新日時が2秒以上前だったファイルだけを再利用します。更新直後のファイルは、同じ時刻の粒度内での書き換えを見逃さないよう、毎回内容を読み直します。読み取り中に変わったファイルは記録しません。キャッシュが使えない場合は、すべてのファイルを読み直します。なお、Gitと同じく、内容を書き換えたうえでサイズと更新日時を元の値へ戻すツールの変更は、作成・変更日時やファイル識別子が変わらない環境では検出できません。`leaf create`とつぼみの保存は、常にファイル全体を読み込んで保存します。復元時も、退避直前の安全確認では各ファイルの内容を読み直します。

## コマンド一覧

通常ヘルプの入口は次の10個です。`sprout leaf --help`、`sprout file restore --help`のように下位のヘルプでも確認できます。GUIと同梱スクリプトは正規構文を使います。

| 入口 | 用途 |
| --- | --- |
| `init` | 初期化 |
| `status` | 現在位置・変更・追跡状態 |
| `go` | 作業フォルダ全体の移動 |
| `leaf` | 葉・履歴・説明・タグ・ラベル・添付 |
| `bud` | 未保存変更の退避・復元 |
| `branch` | ブランチの管理 |
| `file` | 追跡・改名・比較・部分復元・取り出し |
| `trash` | 復旧記録の確認・復旧・完全削除 |
| `maintenance` | 容量・整合性・実体の回収 |
| `serve` | JSON Linesによる実行 |

LEAFは葉ID、一意な接頭辞、ブランチ名、タグ名です。バイナリ出力の`file cat`とJSON Linesの`serve`を除き、各操作は`--json`に対応します。

| 正規構文 | 用途 |
| --- | --- |
| `init [PATH]` | 管理情報を作成する |
| `status [PATH...] [--tracked] [--untracked]` | 状態を確認する |
| `go TARGET / go --branch NAME` | 既定で変更をつぼみに残して移動する。--keep-branch・--reject-changes・--discardは本文参照 |
| `leaf create -m TEXT [--thumbnail IMAGE]` | 現在位置を基に葉を保存する |
| `leaf list [PATH] [--file-id ID] [-n COUNT] [--label LABEL] [--oneline]` | 現在ブランチの履歴、パス変更履歴、素材IDの全保存記録 |
| `leaf tree` | 削除済みブランチ由来を含む全体構造 |
| `leaf show LEAF [--timezone ZONE]` | 葉の内容と注釈 |
| `leaf edit LEAF [--message TEXT] [--note TEXT] [--clear-note]` | メッセージ・メモをまとめて編集する |
| `leaf delete LEAF [--dry-run] [--yes]` | 葉を1枚削除してゴミ箱に残す |
| `leaf prune START_TAG END_TAG / leaf prune --all` | 保護された葉を残して間引く。--dry-run・--yes、取り消し不可 |
| `leaf archive --output DIR [--dry-run]` | 全履歴を静的HTML・JSON・通常ファイルへ取り出す |
| `leaf tag list / leaf tag create NAME [LEAF] [--comment TEXT]` | タグの一覧・作成 |
| `leaf tag comment NAME TEXT / leaf tag delete NAME` | タグのコメント変更・解除と削除 |
| `leaf label list [LEAF]` | 全体のラベル名・利用葉数、または指定した葉の付与情報 |
| `leaf label add LEAF LABEL / leaf label remove LEAF LABEL` | ラベルを付ける・外す |
| `leaf thumbnail show LEAF / leaf thumbnail set LEAF IMAGE` | 葉ごとのサムネイルを確認・登録する |
| `leaf thumbnail delete LEAF / leaf thumbnail export LEAF --output FILE [--force]` | サムネイルを削除・取り出す |
| `leaf thumbnail source show / leaf thumbnail source set PATH` | プロジェクトのサムネイル自動生成元を確認・指定する |
| `leaf thumbnail source clear / leaf thumbnail source apply [--dry-run]` | 生成元を解除し、既存の葉の未登録サムネイルへ適用する |
| `leaf preview list LEAF / leaf preview image LEAF ID` | 添付一覧・選んだ静止画像を取得する |
| `leaf preview add LEAF PATH... / leaf preview replace LEAF ID PATH` | 添付の追加・置き換え。--dry-run・--yes・--media-typeを利用可能 |
| `leaf preview delete LEAF ID / leaf preview export LEAF ID --output FILE [--force]` | 添付の削除・取り出し |
| `leaf preview order LEAF ID... / leaf preview edit LEAF ID [--name TEXT] [--description TEXT]` | 順序・表示名・説明を変更する |
| `bud save [--name NAME] [--keep-files] / bud list` | 未保存変更の退避・一覧 |
| `bud restore BUD / bud rename BUD NAME / bud delete BUD --yes` | 復元・改名・削除。復元成功時は元のつぼみを消費する |
| `branch list [--deleted] / branch create NAME [LEAF] [--switch] [--comment TEXT]` | ブランチの一覧・作成 |
| `branch rename OLD NEW / branch comment NAME TEXT / branch delete NAME` | ブランチの改名・コメント編集・削除 |
| `file track PATH... / file untrack PATH... / file list [--tracked] [--untracked]` | 追跡対象を管理する。追跡解除はファイルを削除しない |
| `file move OLD NEW` | 素材IDを保って移動・改名する |
| `file diff [LEAF_A] [LEAF_B]` | 現在位置や指定した葉と比較する |
| `file restore LEAF PATH... [--discard]` | 選択したパスだけ戻し、現在位置・ブランチ先端を保つ |
| `file export LEAF [PATH...] --output DIR [--force] / file cat LEAF PATH` | 保存ファイルを取り出す。catはバイナリ標準出力 |
| `trash list / trash show ID / trash restore ID [--dry-run] / trash purge ID [--dry-run] [--yes]` | 復旧記録を確認・復旧・完全削除する |
| `maintenance stats / maintenance doctor [--report] / maintenance gc [--dry-run]` | 件数・容量、整合性、不要な実体の回収 |
| `serve` | 正規構文とaliasを同じJSON Linesプロトコルで実行する |

### 手打ち用alias

通常ヘルプでは正規構文を中心に表示し、`sprout --help-aliases`で次の15パターンを確認できます。結果、JSON、終了コード、安全確認は対応先と同じです。

| alias | 正規構文 |
| --- | --- |
| `commit -m TEXT` | `leaf create -m TEXT` |
| `log [PATH] / log --file-id ID` | `leaf list [PATH] / leaf list --file-id ID` |
| `show LEAF` | `leaf show LEAF` |
| `tree` | `leaf tree` |
| `diff ...` | `file diff ...` |
| `track PATH...` | `file track PATH...` |
| `untrack PATH...` | `file untrack PATH...` |
| `mv OLD NEW` | `file move OLD NEW` |
| `switch NAME` | `go --branch NAME` |
| `stash push` | `bud save` |
| `stash list` | `bud list` |
| `stash pop BUD` | `bud restore BUD` |
| `stash drop BUD` | `bud delete BUD` |
| `tag` | `leaf tag list` |
| `tag NAME [LEAF]` | `leaf tag create NAME [LEAF]` |

Sproutの`track`にはGitのステージング領域がありません。`stash pop`はBUDを明示し、成功するとそのつぼみを消費します。`stash apply`やGitの省略スタック指定は提供しません。`switch`もSproutの移動規則を使い、既定で未保存変更をつぼみに残します。

### オプションに見える入力値

`-`で始まる位置引数は`--`の後へ置きます。引用符だけではオプションとの区別になりません。実際の`--json`などのオプションは区切りより前へ置きます。オプションが受け取る文字列には`--option=value`を使えます。

```powershell
sprout branch comment -- main "-確認待ち"
sprout bud rename -- <bud-id> "-別案"
sprout leaf label add --json -- <leaf-id> --json
sprout leaf edit <leaf-id> --message=--json --note="-確認待ち"
```

### 旧33入口からの対応

次の表は旧CLIからの移行用です。通常の操作には正規構文か合意済みaliasを使います。移行途中に残した旧フラグの入口は廃止しており、表は旧構文すべての互換維持を意味しません。

| 旧入口 | 現在の入口 |
| --- | --- |
| `init` | init |
| `status` | status |
| `go` | go。明示ブランチ・空ブランチ・現在ブランチ保持も同じ入口 |
| `commit` | leaf create（手打ちalias commitも利用可能） |
| `log` | leaf list（alias logも利用可能） |
| `tree` | leaf tree（alias treeも利用可能） |
| `show` | leaf show（alias showも利用可能） |
| `message` | leaf edit --message |
| `note` | 編集はleaf edit --note / --clear-note、閲覧はleaf show |
| `label` | leaf label list/add/remove |
| `tag` | leaf tag list/create/comment/delete。aliasは一覧と作成 |
| `thumbnail` | leaf thumbnail show/set/delete/export |
| `cover` | leaf thumbnail source show/set/clear/apply |
| `preview` | leaf preview list/add/replace/delete/export/order/edit/image。旧metadataはedit |
| `delete-commit` | leaf delete |
| `prune` | leaf prune |
| `archive` | leaf archive |
| `file-history` | leaf list --file-id ID |
| `track` | file track（alias trackも利用可能） |
| `untrack` | file untrack（alias untrackも利用可能） |
| `move` | file move。手打ちaliasはmv |
| `diff` | file diff（alias diffも利用可能） |
| `restore` | 全体はgo、ブランチ保持はgo LEAF --keep-branch、部分復元はfile restore LEAF PATH... |
| `export` | file export |
| `cat` | file cat |
| `bud` | bud save/list/restore/rename/delete |
| `branch` | branch list/create/rename/comment/delete |
| `switch` | go --branch NAME（alias switchも利用可能） |
| `trash` | trash list/show/restore/purge |
| `gc` | maintenance gc |
| `doctor` | maintenance doctor |
| `stats` | maintenance stats |
| `serve` | serve |

コミットの指定には、完全なコミットID、一意に識別できるIDの先頭部分、ブランチ名、またはタグ名を使用できます。

`maintenance gc`は参照されないオブジェクトと、中断などで残った一時ファイル(`object-*`)を削除します。削除前に対象だけ確認したい場合は`--dry-run`を使います。

リポジトリの健全性だけ確認したい場合は`maintenance doctor`を使います。`--report`を付けると、問題があっても終了コード0で結果を返します（GUIはこの形で使います）。登録・参照されているオブジェクトの欠落・内容破損・サイズ不一致・非対応の保存形式、objectsに未登録のオブジェクトファイル、中断中の操作記録、残った一時ファイル、存在しないコミットを指す現在位置を報告します。問題がなければ`OK`を表示し、問題があれば終了コード1で終了します。作業ツリーや追跡状態は変更しません。

容量と重複排除の効果を確認したい場合は`maintenance stats`を使います。objectsテーブルに登録されたオブジェクトの件数・保存サイズの合計、コミット数、追跡パス数に加え、コミット上の論理サイズと実ユニークサイズの差（`Dedup saved`）を表示します。読み取り専用です。

## JSON出力

正規の各操作はコマンド単位の`--json`を受け付け、成功時はstdoutへJSONを1つ出力します。バイナリ原本を出す`file cat`とJSON Linesを使う`serve`は別の出力契約です。期待される失敗は非0の終了コードとstderrの構造化エラーで返します。日本語のパスやメッセージはUnicodeエスケープせず出力します。

```powershell
sprout status --tracked --untracked --json
sprout leaf list -n 5 --json
sprout leaf tree --json
sprout leaf prune first-draft submitted --dry-run --json
sprout leaf delete <commit-id> --dry-run --json
sprout leaf show <commit-id> --json
sprout branch list --json
sprout leaf create -m "first" --json
sprout go --branch ideas --json
sprout maintenance doctor --json
sprout maintenance stats --json
sprout maintenance gc --dry-run --json
```

`leaf thumbnail show/set/delete`は添付情報を返し、削除結果には`deleted: true`を加えます。`leaf thumbnail export`は`{"output": string}`です。`leaf preview list/add/order`は添付情報の配列、`replace/edit`は添付情報、`delete`は添付情報と`deleted: true`、`export`は出力先を返します。追加・置き換えのdry-runは各ファイルのsource・original_name・media_type・size・object_hash・already_stored・additional_bytes・requires_confirmationと、合計のadditional_bytes・requires_confirmationを返します。

`leaf edit`は変更後のメッセージと注釈全体を返します。`leaf label list`の引数なしは`[{"name": string, "leaf_count": number}]`、葉指定の一覧・追加・解除は注釈全体です。`branch create --switch`はブランチ情報に退避した`bud`または`null`を含めます。`branch rename`はid・name・previous_name、`branch delete`はid・name・deleted、`branch comment`はid・name・commentを返します。ブランチのidは不変で、葉やつぼみのbranch_idと照合できます。`leaf tag create/comment`はタグ情報、`leaf tag list`はその配列、`leaf tag delete`はname・deletedを返します。

```text
init:       {"root": string}
file track: {"paths": [string]}
file untrack: {"paths": [string]}
leaf create: {"id": string, "branch": string, "branch_id": string, "created_branch": boolean, "message": string, "removed_paths": [string]}
leaf edit: {"commit_id": string, "message": string, "note": string | null, "note_updated_at": string | null, "labels": [string]}
leaf label list LEAF / add / remove: {"commit_id": string, "note": string | null, "note_updated_at": string | null, "labels": [string]}
leaf tag create/comment: {"name": string, "commit_id": string, "comment": string, "created_at": string}
leaf tag delete: {"name": string, "deleted": true}
file export: {"commit_id": string, "output": string, "paths": [string]}
file restore: {"commit_id": string, "paths": [string]}

leaf prune:
{
  "mode": "between" | "all",
  "dry_run": boolean,
  "start_tag": string | null,
  "end_tag": string | null,
  "removed_commits": [{"id": string, "created_at": string, "message": string}],
  "reclaimable_objects": [string],
  "reclaimable_bytes": number
}

leaf delete:
{
  "dry_run": boolean,
  "commit": {"id": string, "created_at": string, "message": string},
  "parent_id": string | null,
  "moved_branches": [{"id": string, "name": string, "current": boolean}],
  "moved_current": boolean,
  "reconnected_children": [string],
  "rebased_buds": [string],
  "reclaimable_objects": [string],
  "reclaimable_bytes": number
}

maintenance gc / maintenance gc --dry-run:
{
  "dry_run": boolean,
  "removed_objects": number,
  "removed_temps": number,
  "freed_bytes": number,
  "objects": [string],
  "temps": [string]
}
```

`maintenance gc --dry-run --json`の件数と容量は、削除した場合の値です。`objects`は対象オブジェクトのハッシュ、`temps`は一時ファイル名です。

保守用の読み取り系コマンドの主な返却項目は次のとおりです。`maintenance doctor --json`は問題を検出した場合も結果のJSONをstdoutへ出力し、終了コード1で終了します。`issues`の`kind`は人向け表示の先頭と同じ識別子（`missing_object`、`corrupt_object`、`object_size_mismatch`、`unsupported_object_encoding`、`unregistered_object`、`orphan_temp`、`active_operation`、`missing_current_commit`など）、`detail`は対象のハッシュ・ファイル名・説明です。`maintenance stats --json`のサイズはすべてバイト数です。

```text
maintenance doctor:
{
  "ok": boolean,
  "checked_objects": number,
  "issues": [{"kind": string, "detail": string}]
}

maintenance stats:
{
  "commits": number,
  "branches": number,
  "tracked_paths": number,
  "buds": number,
  "objects": number,
  "objects_bytes": number,
  "logical_bytes": number,
  "unique_bytes": number,
  "dedup_saved_bytes": number
}
```

読み取り系コマンドの主な返却項目は次のとおりです。`tracked`と`untracked`は、対応するオプションを指定した場合だけ`status`へ含まれます。`status PATH --json`では`changes`の代わりに`paths`が返ります。`current_commit`は作業ツリーの現在位置のコミットID（コミットがないときは`null`）、`at_branch_tip`はそれが現在のブランチ先端かどうかです。

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

leaf list:
[{
  "id": string,
  "parent_id": string | null,
  "created_at": string,
  "message": string,
  "note": string | null,
  "note_updated_at": string | null,
  "labels": [string]
}]

leaf tree:
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
      "display_name": string,
      "description": string,
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
    "current": boolean,
    "created_at": string
  }],
  "tags": [{
    "name": string,
    "commit_id": string,
    "comment": string,
    "created_at": string
  }],
  "deleted_branches": [{"id": string, "name": string, "comment": string, "created_at": string, "deleted_at": string}],
  "buds": [Bud]
}

bud list --json（一覧）:
[Bud]

bud save --json / bud rename BUD NAME --json / bud delete BUD --yes --json:
Bud

go --json:
{
  "current_commit": string | null,
  "branch": string,
  "branch_id": string,
  "at_branch_tip": boolean,
  "bud": Bud | null,
  "changes": [{"state": string, "path": string}]
}

bud restore BUD --json:
{
  "restored": Bud,
  "saved": Bud | null
}

Bud:
{
  "id": string,
  "name": string,
  "base_commit_id": string | null,
  "branch_id": string,
  "branch_name": string,
  "created_at": string,
  "changes": [{"state": string, "path": string}],
  "files": [{
    "path": string,
    "object_hash": string,
    "size": number,
    "mtime_ns": number,
    "file_id": string
  }]
}

leaf show:
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
    "display_name": string,
    "description": string,
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
    "mtime_ns": number,
    "file_id": string
  }]
}

branch list:
[{
  "id": string,
  "name": string,
  "commit_id": string | null,
  "comment": string,
  "current": boolean,
  "created_at": string
}]

branch list --deleted（削除済みだけを返す）:
[{"id": string, "name": string, "comment": string, "created_at": string, "deleted_at": string}]
```

`leaf show`と`leaf tree`の添付一覧はrole、position、添付IDの順で返します。同じrole内ではpositionが表示順です。Attachmentはid、commit_id、role、position、original_name、display_name、description、media_type、object_hash、size、created_at、updated_atを持ちます。roleとmedia_typeは未知の値も許可します。ブランチ一覧のid、およびコミット・つぼみのbranch_idは不変のブランチIDです。branch_nameは作成時の名前です。

JSONの日時は保存されているUTC表現、`mtime_ns`はナノ秒整数のまま返します。そのため、`leaf show --json`と`--timezone`は同時指定できません。`leaf list --json`と`--oneline`も表示形式が競合するため同時指定できません。

JSONモードで期待されるエラーが起きた場合は、非0で終了し、stdoutを空のまま保ってstderrへ次のJSONを1つ出力します。

```json
{"code":"uncommitted_changes","message":"working tree has uncommitted changes (use --discard to replace them)","details":{"can_discard":true}}
```

復元パスの安全性エラーは`unsafe_restore_path`、部分復元の選択範囲との衝突は`restore_scope_conflict`、復旧中に検出したファイルの衝突は`restore_recovery_conflict`を返します。これらの`details`には`path`と`reason`を含めます。

エラーは常に`code`、`message`、`details`を持ちます。代表的な`code`は、一般的な操作エラーの`sprout_error`、他の操作がロック中の`repository_locked`、未コミット変更がある`uncommitted_changes`、OSまたはSQLite操作の`repository_error`、引数指定の`usage_error`です。GUIから実行する操作の主なエラーには`unknown_commit`、`nothing_to_commit`、`not_initialized`のような個別の`code`があり、対象の値を`details`に持ちます。`message`は英語のままです。`repository_locked`の`details.retryable`と`uncommitted_changes`の`details.can_discard`をGUIの再試行・確認フローに利用できます。

GUIとCLIは同じリビジョンの組み合わせで使用してください。

## 無視パターン (`.sproutignore`)

プロジェクトルートの`.sproutignore`に、追跡したくないファイルのパターンを書けます。書式は次のとおりです。

- 1行に1パターン
- `#` で始まる行はコメント
- `*` などの glob はパス全体とファイル名の両方に照合する（例: `*.tmp`、`Thumbs.db`）
- 末尾が `/` のパターンはディレクトリとその配下を除外する（例: `cache/`）

適用されるのは次の操作だけです。

- ディレクトリを指定した `file track`（配下を走査するとき）
- `status --untracked` の一覧

ファイルを明示して `file track` した場合は、無視パターンより優先して登録されます。すでに追跡中のファイルの変更検出（`status` の added / modified / deleted）には影響しません。`.sproutignore` 自体も通常のファイルとして追跡できます。

## 現在の制限

最初のリリースでは、リモート同期とマージには対応していません。
大きなファイルを頻繁に更新すると、`.sprout/objects`の使用量は増えますが、不要になったオブジェクトは`maintenance gc`で削除できます。

## テスト

```powershell
uv run pytest
```

## ライセンス

Sproutは[MIT License](LICENSE)のもとで公開されています。


### 素材IDと改名をまたぐ履歴

追跡ファイルには内容のハッシュとは独立した不変の`file_id`を割り当てます。`leaf show --json`とつぼみのJSON、archiveに各時点のIDを含めます。`sprout leaf list --file-id <file-id> --json`は全ブランチの同じ素材について、各葉のパス・内容・更新日時を新しい順に返します。内容が同じ保存記録や改名も含みます。`leaf list PATH`は現在ブランチのそのパスの内容変更履歴です。

パスは、NFC正規化と大文字小文字の同一視を行った`path_key`で識別します。追跡パス・コミット・つぼみのそれぞれで同じ`path_key`のパスを保存できず、OSを問わず`path_case_conflict`で拒否します（`a`と`A/b`のようなファイルとフォルダの衝突も同様です）。保存時の表記は表示と復元で維持します。`maintenance doctor`は`path_key`の不整合を`invalid_path_key`、衝突を`path_conflict`として報告します。

大文字小文字や表記だけの改名は、`sprout file move Logo.png logo.png`でも、エクスプローラーなど外部での改名でも行えます。外部での改名は`status`と`file diff`に`renamed`（JSONでは`previous_path`付き）と表示し、次の保存で素材IDを維持したまま新しい表記を記録します。フォルダの表記の変更も同様です。`file track`に別の表記を指定した場合も、同じファイルなら表記の更新だけを行います。

`sprout file move`での改名・移動はIDを維持します。コピー、新規登録、追跡解除後の再登録には別IDを割り当て、同じ内容でも別素材として扱います。追跡を続ける同じパスへの上書きは、外部アプリの一時ファイルによる保存も含めて同じIDを維持します。外部での改名は推定せず、新しいパスを登録すると新IDです。削除をコミットした後に同名ファイルを登録した場合も新IDになります。観測していない削除と同名再作成は、追跡中の同じパスへの上書きとして扱います。

ブランチ分岐・全体復元・つぼみ復元では保存されたIDとパスの対応を戻します。部分復元で、選択外のパスに同じIDがある場合や、選択したパスが別IDに結び付いている場合は`file_identity_conflict`で拒否します。全体復元か、追跡の整理を明示してから復元してください。IDだけが変わった再登録も未保存変更となり、コミットできます。日時だけの変更の扱いは変わりません。

葉のゴミ箱からの復旧も保存したIDを戻します。素材IDの登録情報は履歴や復旧項目の参照を失わないよう保持し、gcは内容の実体だけを従来どおり回収します。内容が同じ素材の重複排除は維持します。


### 葉全体のpreviewの表示名・説明

previewには原本のファイル名とは別に表示名・説明を保存できます。表示名はNFC正規化と前後の空白除去後に256 Unicode文字まで、保存値に改行・NULは含めません。説明はNFC正規化後に2万文字までで改行を保持し、NULを拒否します。未設定の表示名は原本のファイル名で表示します。

```powershell
sprout leaf preview edit <commit> <preview-id> --name=確認用 --description=初稿
sprout leaf preview edit <commit> <preview-id> --name= --description=
```

previewは葉全体を確認するための添付資料です。追跡対象外のファイルも添付でき、個別素材の指定は必要ありません。重要なpreviewは並べ替えて一覧の上へ置けます。順序を変えてもサムネイルを自動変更したり、未選択メディアを読み込んだりはしません。

内容の置き換えと並べ替えでは表示名・説明を保持します。置き換えは添付ID・表示位置・最初の登録日時も保持します。削除や置き換えの取り消しでは保存した原本・表示名・説明・順序を復旧します。その後にメタ情報や添付一覧が編集されていれば、上書きを避けて復旧を拒否します。ファイル自身の素材ID、改名・移動をまたぐ履歴、サムネイル自動生成元はそれぞれ従来どおり利用できます。

CLI・JSON・GUI・archiveに`display_name`、`description`を含めます。GUIでは各previewの「表示名・説明を編集」で設定・解除できます。正規CLIは`leaf preview list/add/replace/delete/export/order/edit/image`です。


### 静止画像previewの表示キャッシュ

選択した静止画像の表示用PNGと、原本の形式・寸法・表示寸法を`.sprout/preview-cache/`へ保存し、再表示に使います。キャッシュの識別には原本SHA-256、生成処理の版、Pillowの版、表示サイズ・検証上限、プロジェクトの場所と原本オブジェクトのファイル情報を含めます。内容や表示条件が変われば作り直し、別プロジェクトの結果を混同しません。キャッシュヒット時は原本の取得・展開・デコードを省きます。原本のencodingは別途確認し、原本が欠落した場合も通常の検証で拒否します。

完成したキャッシュ項目の合計上限は256 MiBで、最終利用日時の古い項目から破棄します。1項目は32 MiBまでとし、保存できない大きさや、容量確保・読み書きに失敗した場合は通常の生成結果をそのまま返します。容量に数えるのはJSON内の表示用画像と情報で、ロックファイルや生成中の一時ファイルは含みません。原本・履歴・ゴミ箱の保存容量とは別です。

キャッシュはチェックサム・形式・寸法を検査し、欠落や破損があれば再生成します。生成結果は一時ファイルへ書いてからまとめて公開し、同時生成と清掃にはプロジェクトごとの書き込みロックを使います。生成途中で中断したファイルは完成品として読まず、次の保守時に回収します。同時要求で保存できない場合も、生成した正しい画像を返します。GUIへは画像データ自体を渡すため、清掃中も表示済みの画像を維持できます。

原本は「画像を表示」で対象を選ぶまで取得・デコードしません。既存の作業ツリーハッシュキャッシュ（worktree-cache.db）と、GUIのサムネイル用メモリキャッシュとは別の補助情報です。このキャッシュがなくても閲覧を再開できます。履歴復元・archive・バックアップの必須データには含めません。

消去する場合はGUIと、そのプロジェクトを使用中のCLIを終了し、プロジェクト直下で次を実行してください。次に画像を選んだときに再生成します。

```powershell
Remove-Item -LiteralPath '.sprout\preview-cache' -Recurse -Force
```
