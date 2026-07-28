
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

- `main` へ直接コミットしない。作業ごとに専用ブランチを作成する。
- ブランチ名は `codex/<task-id>-<short-description>` とする。
  - 例: `codex/task-42-add-export-command`
- Backlog のタスクがある場合は、ブランチ名とコミットメッセージにタスク番号を含める。
- 1つのコミットには、1つの論理的な変更だけを含める。
- 作業途中の「修正」「微調整」コミットは、PR作成前に squash する。
- `main` への取り込みは squash merge に統一する。
- 既にリモートへ公開された `main` の履歴を書き換えない。
- 自分専用で、まだ共有していないブランチに限り、必要に応じて rebase や commit の整理を行う。
- マージ後は、不要になったローカル作業ブランチを削除する。
- コミット前に次を確認する。
  1. テストが成功していること
  2. 意図しない変更がないこと
  3. 作業ツリーの状態
  4. 直近のコミット履歴
- コミットメッセージは命令形の短い英語で書き、変更内容を具体的に表す。
  - 例: `Add shell completion for branch commands`
  - 例: `Fix restore handling for deleted paths`
- 履歴整理や force push が必要な場合は、実行前にユーザーへ確認する。
