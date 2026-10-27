---
id: TASK-60
title: 上部バーのファイルパネルで追跡ファイルを管理する
status: To Do
assignee: []
created_date: '2026-10-27 15:04'
labels:
  - gui
  - gui-redesign
dependencies:
  - TASK-57
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: low
type: feature
ordinal: 60000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

GUI刷新（doc-1、TASK-51で承認済み）では、旧ステータスタブにあった追跡ファイルの管理を、上部バーの「ファイル」から開くパネルへ移す。

## ゴール

追跡中・未追跡のファイル一覧と、追跡・追跡解除の操作をファイルパネルで行えるようにする。ウィンドウへのドロップで追跡する既存の動作を維持する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 上部バーのファイルからパネルを開閉でき、追跡中と未追跡のファイル一覧が表示される
- [ ] #2 パネルからファイルとフォルダを追跡・追跡解除でき、結果件数が通知される
- [ ] #3 ウィンドウへファイルやフォルダをドロップすると追跡され、マップと上部バーの状態が更新される
- [ ] #4 追跡対象が0件のときなど結果がない操作で警告が表示される
- [ ] #5 パネル操作とドロップのGUIテストがある
<!-- AC:END -->
