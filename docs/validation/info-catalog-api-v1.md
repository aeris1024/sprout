# info／catalog API v1 検証・引き継ぎ

実施日：2026年11月2日。Backlog：TASK-127。

Sprout側API受け入れ済み・資料棚GUIの実結合待ち。資料棚の既存141項目は、この検証の成功件数に含めない。

## 変更と利用方法

`sprout info [--json]`と`sprout catalog [--json]`を追加した。保存形式、既存のleaf show、thumbnail export、file exportのJSON形状は維持した。WindowsではJSONのstdout・stderrをUTF-8へ明示的に設定するため、既定がCP932でも日本語や絵文字を外部アプリで受信できる。

変更対象はRepositoryの取得処理、CLIの登録・表示・JSON文字コード、コマンド一覧の既存テスト、追加APIテスト、再生成スクリプト、README、本検証記録、Backlogタスク。資料棚側のソースは変更していない。

変更ファイル：`src/sprout/repository.py`、`src/sprout/cli.py`、`tests/test_catalog.py`、`tests/test_cli_aliases.py`、`tests/test_final_cli.py`、`scripts/verify_catalog_api.py`、`README.md`、`docs/validation/info-catalog-*`、`backlog/tasks/task-127 - Add-info-and-catalog-API-v1.md`。対応コミットは`git log --grep='TASK-127 Add info and catalog API v1'`で確認できる。

資料棚の設定に指定できる検証済み実行ファイル：

```text
C:\Users\k-nis\Workbench\work\Sprout\.venv\Scripts\sprout.exe
```

バージョン表示は`sprout 1.0.0`。このexeは現在のSproutソースを参照する開発環境のコンソールエントリーポイントであり、`.venv`とリポジトリを維持して利用する。exe単体を別の場所へ移動しない。グローバルPATHの変更は不要。別のチェックアウトでは`uv sync --dev`で環境を準備する。

登録元のプロジェクトを作業ディレクトリとして、上記exeに`info --json`または`catalog --json`を渡す。詳細と書き出しにはcatalogの完全commit_idをそのまま渡す。

```powershell
$sprout = 'C:\Users\k-nis\Workbench\work\Sprout\.venv\Scripts\sprout.exe'
& $sprout info --json
& $sprout catalog --json
& $sprout leaf show <完全コミットID> --json
& $sprout leaf thumbnail export <完全コミットID> --output <新規画像ファイル> --json
& $sprout file export <完全コミットID> --output <新規フォルダ> --json
```

## 実CLIの応答

[実行記録JSON](info-catalog-api-v1.json)に35コマンド分の引数・作業ディレクトリ・終了コード・stdout・stderrと、完全なinfo/catalogを保存した。以下はそのinfoを整形したもの。成功時は終了コード0、stderrは空で、stdoutにはこのオブジェクト一つだけが出る。

```json
{
  "api_version": 1,
  "sprout_version": "1.0.0",
  "repository": {
    "id": "5756f2bf-4f40-4aae-8aae-47985b111a49",
    "root": "C:\\Users\\k-nis\\Workbench\\work\\Sprout\\.test-tmp\\catalog-api\\run-8cyn2l3o\\画像 project",
    "created_at": "2026-11-02T06:34:16.909140+00:00"
  },
  "capabilities": ["info.json.v1", "catalog.json.v1"]
}
```

catalogの完全な応答は実行記録の`catalog`および該当コマンドの`stdout`にある。終了コード0、stderrは空。`api_version`と上記と同じ`repository`を持ち、`variants`にはWebP・PNG・JPEGの3件が日時降順で入る。その先頭の版は次のとおり。

```json
{
  "commit_id": "f89a750dd40840c09a42aee52df9c4e3",
  "created_at": "2026-11-02T06:34:20.711891+00:00",
  "message": "WEBP の版",
  "tags": [
    {"name": "Alternate", "comment": "", "created_at": "2026-11-02T06:34:21.592645+00:00"},
    {"name": "版2", "comment": "", "created_at": "2026-11-02T06:34:21.169565+00:00"}
  ],
  "note": "確認 メモ AbC",
  "note_updated_at": "2026-11-02T06:34:22.006546+00:00",
  "labels": ["Approved"],
  "thumbnail": {
    "commit_id": "f89a750dd40840c09a42aee52df9c4e3",
    "role": "thumbnail",
    "original_name": "preview 2.webp",
    "media_type": "image/webp",
    "object_hash": "1b8fbd8596e577a836cc006cf812613d7ede148e30aa450d45c25db4dca23cdb",
    "size": 76,
    "created_at": "2026-11-02T06:34:20.711891+00:00",
    "updated_at": "2026-11-02T06:34:20.711891+00:00"
  }
}
```

未初期化の専用フォルダでのinfoとcatalogは、ともに終了コード1、stdoutは空、stderrは次のJSON一つだった。

```json
{"code":"not_initialized","message":"not inside a Sprout project (run 'sprout init')","details":{}}
```

通常表示ではinfoにバージョン・API版・ID・ルート・作成日時・capabilities、catalogに完全ID・タグ名・メッセージを表示する。タグなしでは`No tagged variants.`と表示する。

## 一貫性・状態・復旧

`Repository.catalog()`は`connect()`を一度だけ呼び、明示的な`BEGIN`の後にリポジトリ情報、タグ、タグ付きコミット、注釈、thumbnailを読む。タグのdistinct commit_idから対象を絞り、通常ファイル一覧、画像デコード、内容ハッシュ再計算、全履歴・全オブジェクトの読み込みは行わない。注釈の取得には既存のDB接続内一括取得処理を使う。日時はUTCの時刻として比較し、同日時は完全ID順。タグ名とラベルは保存値をそのまま比較する。

並行更新テストは、catalogがタグ・コミットを読んだ後に別接続のWALトランザクションでタグ名・メモ・ラベル・thumbnail名を更新する。進行中のcatalogでは全て更新前、次のcatalogでは全て更新後になることを確認した。

正常状態ではDBの論理ダンプと作業ファイルの内容・mtimeを前後比較し、追跡状態・現在位置・ブランチ先端を含め変更がないことを確認した。SQLiteのWAL等の管理ファイルのバイト単位不変性は保証しない。

既存の`Repository.discover()`は保存形式を検証し、`active_operation`がある場合は復旧計画を検証してロックを取得し、`_recover_pending_materialization()`を実行する。中断操作のロールバック、管理データ更新、一時フォルダ清掃が発生し得る。自動復旧の成功、不正な復旧計画、復旧時のロック取得失敗を追加テストで確認した。通常の書き込みロックは読み取りを妨げない。DB排他ロックで取得不能ならエラーになり、空一覧には置き換えない。

## 再生成と期待結果

Sproutルートで実行する。

```powershell
.venv\Scripts\python.exe scripts\verify_catalog_api.py --executable .venv\Scripts\sprout.exe
```

毎回`.test-tmp/catalog-api/run-<一意な名前>`を新規作成する。既存の制作プロジェクトを引数に取らず、既存プロジェクトや既存出力を削除・再利用しない。別の保存先は`--output <親フォルダ>`で指定できる。

今回の専用データは`C:\Users\k-nis\Workbench\work\Sprout\.test-tmp\catalog-api\run-8cyn2l3o`。`空 project`はコミットなしでcatalogが空配列。`画像 project`は次の3版を持つ。再生成時のUUID・コミットID・日時は変わる。

| 版 | タグ | 添付画像 | 元画像のサイズ |
|---|---|---|---|
| JPEG の版 | 版0 | preview 0.jpg | 637 bytes |
| PNG の版 | 版1 | preview 1.png | 91 bytes |
| WEBP の版 | Alternate、版2 | preview 2.webp | 76 bytes |

各版には`資料 file.txt`と`textures/色 data.bin`を保存する。WebPの版にはメモとApprovedラベルを付ける。最後に作業ファイルを未保存の内容へ変更し、参照・書き出しで維持されることを確認する。画像のエンコード結果はPillow等の版により変わり得るため、スクリプトは生成した原本との実測一致を検証する。

`export-preview ...`は元画像とバイト単位で一致する。`files-<完全ID>`にはleaf showと同じ2ファイルがあり、size・SHA-256・pathsが一致する。既存の出力先への再書き出しは拒否される。実行記録は生成先の`verification.json`にも保存する。

## 自動テスト

追加テストは`tests/test_catalog.py`。既存CLI一覧テストは新コマンドを含む期待値へ更新した。

```powershell
.venv\Scripts\python.exe -m pytest -q --basetemp .test-tmp/task127-full -p no:cacheprovider --junitxml=.test-tmp/task127-pytest.xml
.venv\Scripts\python.exe -m pytest tests/test_catalog.py -q --basetemp .test-tmp/task127-final-api -p no:cacheprovider --junitxml=.test-tmp/task127-api.xml
Set-Location gui
node node_modules/vitest/vitest.mjs run
```

[テスト件数・スキップ理由](info-catalog-test-results.json)はJUnit XMLから集計した。

| 実行 | 成功 | 失敗 | スキップ |
|---|---:|---:|---:|
| Python全体（追加APIの初期20件を含む） | 779 | 0 | 20 |
| 上記のうち既存Pythonテスト | 759 | 0 | 20 |
| 最終の追加APIテスト（実exe連携テストを加えた21件） | 21 | 0 | 0 |
| GUI Vitest（19ファイル） | 284 | 0 | 0 |

Python全体の実行は384.86秒。全体実行後に実exe連携をpytestにも組み込み、追加API21件を再実行した。重複を除くPythonの確認結果は既存759成功＋追加21成功、失敗0、スキップ20。スキップはシンボリックリンク作成権限不足18件と、Windowsの大文字小文字比較に適用しない2件で、成功には含めない。既存exportの配置・内容・mtime・上書き保護・JSON／通常表示のテストも全体実行に含む。

初回の部分実行ではテストデータの日時形式とNULLコメントが既存DB制約に合わず修正した。DBスキーマは変更していない。既存の空コメントは空文字を保持する。Bash補完テストはサンドボックス内でMSYS起動を拒否されたため、Python全体は通常環境で再実行した。`pnpm test`はpnpm本体のメタデータ取得に失敗し、導入済みVitestの直接起動で検証した。GUIには既存のjsdom Canvas未実装メッセージが出るが、テスト失敗はなかった。

資料棚の実GUIでの登録・再同期・画像表示・代表版・永続書き出しは未実施。API検証をGUI結合完了として扱わない。リリース、mainの更新、タグ作成は今回の対象外。
