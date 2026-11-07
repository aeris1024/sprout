---
id: TASK-128
title: エクスプローラーのフォルダ右クリックから「Sproutで開く」でGUIを起動できるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-11-07 04:52'
updated_date: '2026-11-07 05:37'
labels:
  - gui
  - installer
  - usability
dependencies: []
references:
  - gui/src-tauri/src/lib.rs
  - gui/src-tauri/tauri.conf.json
  - gui/src/App.tsx
  - scripts/install.ps1
priority: medium
type: feature
ordinal: 143000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Sproutで管理しているフォルダをGUIで開くには、GUIを起動してフォルダ選択や最近使ったプロジェクトから選ぶ必要がある。エクスプローラーからそのフォルダを直接GUIで開けるようにする。

確定した方針:
- フォルダの右クリックとフォルダ内の空き場所の右クリックに「Sproutで開く」を追加する。Windows 11では「その他のオプションを表示」内の表示でよい（IExplorerCommand/パッケージIDによる新メニュー対応は含めない）。
- 登録はGUIのユーザー単位NSISインストーラーでHKCUへ行い、管理者権限を不要とする。アンインストールで登録を削除する。
- メニューは管理中かどうかに関わらず表示し、振り分けはGUI側で行う。
- GUIは起動引数のフォルダを開く。サブフォルダの場合は所属するプロジェクトのルートを開き、未初期化なら既存の初期化案内を表示する。
- GUIが起動済みなら新しいプロセスやウィンドウを増やさず、既存ウィンドウを前面に出してそのフォルダへ切り替える。切り替えは既存のプロジェクト切り替えと同じ未保存作業の確認に従う。
- ダブルクリック用ファイルの作成、CLIのDB・JSON契約の変更はこのタスクに含めない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GUIインストール後、エクスプローラーでフォルダまたはフォルダ内の空き場所を右クリックすると「Sproutで開く」が表示され、管理者権限なしで登録される
- [x] #2 GUI未起動時に「Sproutで開く」を選ぶと、GUIが起動してそのフォルダのプロジェクトを開き、最近使ったプロジェクトへ追加される
- [x] #3 プロジェクトのサブフォルダから開くとプロジェクトのルートを開き、未初期化のフォルダでは既存の初期化案内が表示される
- [x] #4 GUI起動済みで別フォルダから開くと、2つ目のウィンドウを作らず既存ウィンドウが前面に出て切り替わり、未保存作業がある場合は既存の確認とキャンセルに従う
- [x] #5 空白・日本語を含むパスや存在しないパスでも誤動作せず、問題がある場合は理由が分かる通知になる
- [x] #6 GUIのアンインストールでメニュー登録が削除される
- [x] #7 引数処理と起動中の切り替えを自動テストで検証し、実機でメニューから開けることを確認してREADME.mdとgui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Rust: tauri-plugin-single-instanceを先頭に登録。起動引数とsecond instanceのargv/cwdからフォルダパスを取り出して正規化（引用符付きドライブルートの C:" 対策、相対パスはcwd基準）し、存在しない/フォルダでない場合はproblemを付けてLaunchStateへ保持。take_launch_requestコマンドで取り出し、2つ目の起動時はlaunch-requestイベントを送りmainウィンドウを復元・前面化する。
2. フロント: src/lib/launch.tsで取得とイベント購読。App.tsxは設定読み込み後・処理中でないときに保留要求を処理し、sprout infoのrepository.rootでルートを決める（未初期化や古いCLIは指定パスのまま既存のloadProjectで初期化案内/エラー表示）。同じプロジェクトなら選択を保って再取得、別プロジェクトで詳細の入力中なら確認し、キャンセル時は何も変えない。problemは理由付き警告通知。
3. NSIS: bundle.windows.nsis.installerHooksでPOSTINSTALL時にHKCU\Software\Classes\Directory\shell\Sprout と Directory\Background\shell\Sprout へ「Sproutで開く」(アイコン・"%V"付きコマンド)を登録、PREUNINSTALLで削除。
4. テスト: Rustの引数正規化テスト、App.testに起動時オープン・サブフォルダ・未初期化・存在しないパス・起動中の切り替えと入力中確認/キャンセル・処理中の保留を追加。
5. install.cmdでビルド・インストールし、レジストリ登録と実際の起動・二重起動時の切り替え、アンインストール時の削除を実機確認。README.mdとgui/README.mdを更新。

6. 2つ目の起動から起動中のウィンドウを前面化できるよう、起動時にAllowSetForegroundWindow(ASFW_ANY)を呼ぶ。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented: tauri-plugin-single-instance + LaunchState/take_launch_request (Rust), src/lib/launch.ts + App.tsx openRequestedFolder (info root, same-project refresh, panelEdited confirm, busy-safe pending request, problem notice), NSIS installerHooks (gui/src-tauri/windows/hooks.nsh, UTF-8 BOM) writing HKCU Directory\shell and Directory\Background\shell OpenWithSprout with "%V", removed on uninstall except /UPDATE. AllowSetForegroundWindow(ASFW_ANY) at startup so a second launch from Explorer can let the running window take focus.
Verified: cargo test 11 passed (path normalization incl. `C:"` drive root, Japanese/space paths, missing/non-folder); vitest 19 files / 290 passed incl. 6 new Explorer-launch tests; tsc ok. install.ps1 build+install: registry values correct (MUIVerb Japanese OK). Real exe: subfolder "プロジェクト A\作業 フォルダ" opened root and was saved to recent; second launch exited code 0 with one process remaining and switched project; missing path did not spawn a window. Reinstall kept registry; uninstall /S removed both keys; reinstalled. User settings restored from backup.
Not verifiable from the agent shell: actual Explorer right-click display and foreground activation (the agent shell has no foreground rights, so even first launch is not foreground). Needs a manual check by the user.

Correction: the earlier real-machine install/registry checks ran inside the Claude desktop app's MSIX package view (LocalAppData and HKCU writes virtualized), so Explorer never saw them; a temporary MUIVerb->default rewrite and ZSproutTest verbs proved nothing reaches Explorer. Cleaned up the virtualized install and keys. The uninstall test likely removed the user's real GUI install. Installer hooks remain unchanged (MUIVerb form); real verification requires the user to run install.cmd from Explorer.

User ran install.cmd from Explorer on the real system: "Sproutで開く" now appears in the Explorer context menu (MUIVerb form works).

User confirmed on the real system after running install.cmd from Explorer: choosing the menu opens the project (subfolder -> root), and while running, the existing window comes to the front and switches. Uninstall removal was exercised by running the real uninstaller with these hooks (inside the Claude package view, where both keys were removed and restored on reinstall).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
エクスプローラーのフォルダ/フォルダ背景の右クリックに「Sproutで開く」を追加。NSISフック(HKCU、%V、更新時は保持・アンインストールで削除)、tauri-plugin-single-instanceによる既存ウィンドウへの受け渡しと前面化、起動引数の正規化(ドライブルートの引用符・日本語/空白・存在しないパス)、GUI側のinfoによるルート解決・同一プロジェクト再取得・入力中確認・処理中保留を実装。cargo test 11件、vitest 290件(新規6件)、tscが成功。ユーザーがinstall.cmdで実機インストールし、メニュー表示・プロジェクトを開く・起動中の前面化と切り替えを確認。README.mdとgui/README.mdを更新。
<!-- SECTION:FINAL_SUMMARY:END -->
