---
id: TASK-9
title: Windowsで大文字小文字が異なるパス指定を正しく照合する
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-15 16:16'
updated_date: '2026-07-19 19:17'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
modified_files:
  - src/sprout/repository.py
  - tests/test_repository.py
priority: low
type: bug
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 問題

追跡パスはPOSIX形式の文字列としてDBに保存され、照合は大文字小文字を区別する。Windowsのファイルシステムは通常大文字小文字を区別しないため、ユーザーが`FOO.TXT`と入力しても実体が`foo.txt`なら不一致になり得る。ファイルが存在する場合は`Path.resolve()`が実際のケースへ正規化するので概ね問題ないが、`must_exist=False`の経路(削除済みファイルの`untrack`、`move`の移動先など)では入力されたままのケースが使われ、登録済みパスと照合できず黙って空振りする。

## 修正方針

`_relative_file`で`must_exist=False`かつパスが存在しない場合、存在する最も深い祖先ディレクトリまでを`resolve()`でケース正規化し、残りの構成要素はそのまま連結する。さらに`untrack`の照合時は、`os.path.normcase`相当の比較(Windowsのみケースを無視)で`tracked_paths`と突き合わせる方法もある。プラットフォーム分岐を入れる場合は`os.name == "nt"`で判定し、macOS/Linuxの従来動作(ケース区別)は変えないこと。テストはWindowsでのみ意味を持つ部分に`pytest.mark.skipif`を使う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Windowsで、大文字小文字だけが異なる入力でも削除済み追跡ファイルをuntrackできる
- [x] #2 ケース照合の挙動がテストで検証されている(非Windows環境ではスキップ可)
- [x] #3 macOS/Linuxの従来動作は変わらない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Windowsだけ追跡パス照合用キーをnormcaseで正規化する。
2. untrackの完全一致・子孫一致に正規化キーを使い、非Windowsは従来のケース区別を保つ。
3. Windows限定テストと非Windowsの回帰テストを追加する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Windowsではos.path.normcaseによる追跡パス照合をuntrackへ適用し、非Windowsでは文字列を変更しない。Windowsケース違いテストが成功し、非Windows回帰テストも追加した。全体検証: uv run pytest (41 passed, 2 skipped)。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Windowsで削除済み追跡ファイルをケース違いの指定でもuntrackできるようにし、プラットフォーム別の回帰テストを追加した。全テスト成功。
<!-- SECTION:FINAL_SUMMARY:END -->
