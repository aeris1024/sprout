# Sprout GUI

Sprout GUIは、Tauri 2、React、TypeScript、Viteで構築したWindows向けデスクトップアプリです。
GUIは`.sprout`を直接操作せず、Rust側の共通IPCコマンドから`sprout <command> --json`を実行します。

## 必要な環境

- Windows 10または11とWebView2 Runtime
- Node.js 20.19以降
- pnpm
- Rust stable（MSVC toolchain）
- Visual Studio 2022のDesktop development with C++とWindows SDK
- PATH上のSprout CLI、またはGUIの「CLI設定」で指定する実行ファイル

リポジトリのルートからSprout CLIをインストールする場合は次を実行します。

```powershell
uv tool install .
sprout --help
```

Rustを初めて導入した直後は、ターミナルを再起動して`cargo`へのPATHを反映してください。

## 開発

`gui`ディレクトリで依存関係を準備し、Tauriの開発ウィンドウを起動します。

```powershell
cd gui
pnpm install
pnpm tauri dev
```

フロントエンドだけをブラウザで確認する場合は`pnpm dev`を使えます。ただし、フォルダ選択、設定保存、Sprout CLI呼び出しはTauriウィンドウ内でのみ動作します。

## 検証とビルド

```powershell
pnpm test
pnpm build
cargo test --manifest-path src-tauri/Cargo.toml
pnpm tauri build
```

`pnpm tauri build`の成果物は`gui/src-tauri/target/release/bundle/`へ作成されます。

## 初回利用

1. PATHに`sprout`がない場合は「CLI設定」で実行ファイルを指定します。
2. 「フォルダを開く」から作業フォルダを選択します。
3. 未初期化のフォルダでは、確認画面から`sprout init --json`を実行できます。
4. 初期化済みなら`status --tracked --untracked --json`の結果を表示します。

## 日常操作

- **ステータス**: 変更、追跡中、未追跡のファイルを確認します。「ファイルを追加」「フォルダを追加」、未追跡一覧、またはウィンドウへのドラッグ&ドロップで追跡を開始できます。追跡中一覧の「追跡解除」は作業ファイルを削除しません。
- **コミット**: メッセージを入力し、必要なら2 MiB以下のPNG・JPEG・WebPサムネイルを選んでスナップショットを作成します。
- **履歴**: コミットを選ぶとID、日時、ブランチ、サムネイル名、保存ファイルを確認できます。「このコミットを復元」で作業ツリーへ復元します。
- **ツリー**: 現在残っているブランチだけでなく、削除済みブランチで作成されたコミットも親子関係付きで俯瞰できます。静止画像サムネイル、現在のブランチ先端、タグ、選択中コミットを表示し、ノードから復元、ブランチ切り替え、サムネイル登録へ進めます。子ツリーは折りたたみ可能で、80件を超える表示は段階的に追加します。
- **ブランチ**: 現在のブランチとコメントを確認し、新しいブランチの作成や既存ブランチへの切り替えを行います。

ブランチ切り替えまたは復元が未保存変更によって拒否された場合だけ、追跡対象の変更を破棄して再実行する確認画面が表示されます。破棄は取り消せないため、必要な変更を先にコミットしてください。操作中は他の操作ボタンが無効になり、ウィンドウへフォーカスを戻すと状態が自動更新されます。

ツリーのサムネイルはPNG・JPEG・WebPだけを画面内へ近づいた時点で読み込みます。取得結果はプロジェクト、コミットID、オブジェクトハッシュ、メディアタイプ単位でメモリへキャッシュされます。音声、動画、アニメーション画像、3Dモデルはツリー内で自動再生・描画しません。

最近使ったプロジェクトとCLIパスは、Tauri StoreによりOSのアプリデータ領域へ保存されます。
Sprout CLIがロック中の場合は再試行ボタンを表示し、CLIが見つからない場合はCLI設定を開きます。

初期版はPATHまたは手動指定のCLIを子プロセスとして起動します。将来sidecarを同梱する場合も、Rust側の実行ファイル解決だけを差し替え、フロントエンドのIPC契約は維持します。
