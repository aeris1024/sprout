
<!-- BACKLOG.MD GUIDELINES START -->
<!-- backlog.md-instructions-version: 1.48.0 -->
<CRITICAL_INSTRUCTION>

## Backlog.md Workflow

This project uses Backlog.md for task and project management.

**For every user request in this project, run `backlog instructions overview` before answering or taking action.**

Use the overview to decide whether to search, read, create, or update Backlog tasks.

Before task lifecycle actions, read the matching detailed guide:
- `backlog instructions task-creation` before creating or splitting tasks
- `backlog instructions task-execution` before planning, changing status or assignee, adding a plan or implementation notes, or implementing task work
- `backlog instructions task-finalization` before checking acceptance criteria, writing final summaries, or moving tasks to terminal statuses

Use `backlog <command> --help` before running unfamiliar commands. Help shows options, fields, and examples.

Do not edit Backlog task, draft, document, decision, or milestone markdown files directly. Use the `backlog` CLI so metadata, relationships, and history stay consistent.

</CRITICAL_INSTRUCTION>
<!-- BACKLOG.MD GUIDELINES END -->

## Git Workflow

- 作業ごとにブランチを作成し、`main` で直接作業しない。PRは作らない。
- ブランチ名は `task-<番号>-<短い説明>` とする。タスクがない作業は `<短い説明>` だけでよい。
  - 例: `task-42-add-export-command`
- コミットは意味のある単位で作る。作業途中の「修正」「微調整」コミットは、マージ前にまとめる。
- 完了したら `main` へ `git merge --ff-only` で取り込み、push して作業ブランチを削除する。
  - `main` が先に進んでいる場合は、作業ブランチを `main` に rebase してから取り込む。
- コミット前に、テストが成功していることと、意図しない変更がないことを確認する。
- コミットメッセージは命令形の短い英語で書く。Backlog のタスクがある場合は先頭にタスク番号を付ける。
  - 例: `TASK-42 Add shell completion for branch commands`
- push 済みの `main` の履歴は書き換えない。force push が必要な場合は、実行前にユーザーへ確認する。
