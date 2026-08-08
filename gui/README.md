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

最近使ったプロジェクトとCLIパスは、Tauri StoreによりOSのアプリデータ領域へ保存されます。
Sprout CLIがロック中の場合は再試行ボタンを表示し、CLIが見つからない場合はCLI設定を開きます。

初期版はPATHまたは手動指定のCLIを子プロセスとして起動します。将来sidecarを同梱する場合も、Rust側の実行ファイル解決だけを差し替え、フロントエンドのIPC契約は維持します。
