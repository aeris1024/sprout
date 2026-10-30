"""Render a Sprout-independent static archive: plain HTML, JSON and text only.

The pages use inline CSS and relative links so that a copied archive opens in
any local web browser without a server, CDN, script runtime, Sprout or Python.
"""

from __future__ import annotations

import html
import json
import posixpath
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

ARCHIVE_FORMAT = "sprout-static-archive"
ARCHIVE_FORMAT_VERSION = 1
INCOMPLETE_MARKER = "SPROUT-ARCHIVE-INCOMPLETE.txt"
INCOMPLETE_SUFFIX = ".sprout-archive-incomplete"
SHORT_ID_LENGTH = 12
_UNSAFE_NAME_CHARS = re.compile(r'[\x00-\x1f<>:"/\\|?*]')
_WINDOWS_RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.IGNORECASE)

STYLE = """
body { font-family: system-ui, sans-serif; margin: 1.5rem; color: #1d2a1f; background: #fbfcf8; }
a { color: #2f6b2f; }
table { border-collapse: collapse; width: 100%; }
th, td { border-bottom: 1px solid #d8e0d2; padding: .35rem .5rem; text-align: left; vertical-align: top; }
th { background: #eef3e8; }
code { font-family: ui-monospace, monospace; }
.note { white-space: pre-wrap; background: #f1f4ec; padding: .5rem; }
.label, .tag, .branch { display: inline-block; border: 1px solid #9bb38f; border-radius: .7rem; padding: 0 .45rem; margin: 0 .2rem .2rem 0; font-size: .85em; }
.deleted { color: #8a5a44; }
.preview { margin: 1rem 0; padding: .75rem; border: 1px solid #d8e0d2; }
.preview img, .preview video, .thumbnail img { max-width: 100%; max-height: 32rem; }
"""


def snapshot_directory_name(created_at: str, commit_id: str, id_length: int = SHORT_ID_LENGTH) -> str:
    """Name a snapshot by its UTC commit time and short ID, safe on Windows."""
    moment = datetime.fromisoformat(created_at).astimezone(timezone.utc)
    return f"{moment.strftime('%Y%m%dT%H%M%S.%fZ')}_{commit_id[:id_length]}"


def safe_file_name(name: str) -> str:
    """Make an attachment's original name usable as one file name everywhere."""
    cleaned = _UNSAFE_NAME_CHARS.sub("_", name).rstrip(" .")
    if cleaned in {"", ".", ".."}:
        cleaned = "attachment"
    if _WINDOWS_RESERVED.match(cleaned):
        cleaned = f"_{cleaned}"
    return cleaned


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _href(from_dir: str, target: str) -> str:
    relative = posixpath.relpath(target, from_dir or ".")
    return "/".join(quote(part) for part in relative.split("/"))


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang=\"ja\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{_e(title)}</title>\n<style>{STYLE}</style>\n</head>\n<body>\n"
        f"{body}\n</body>\n</html>\n"
    )


def _chips(values: list[str], kind: str) -> str:
    return "".join(f'<span class="{kind}">{_e(value)}</span>' for value in values)


def _commit_link(model: dict[str, Any], from_dir: str, commit_id: str | None) -> str:
    if commit_id is None:
        return "(なし)"
    commit = model["commits_by_id"].get(commit_id)
    if commit is None:
        return f"<code>{_e(commit_id[:SHORT_ID_LENGTH])}</code>"
    href = _href(from_dir, commit["directory"] + "/index.html")
    return f'<a href="{href}"><code>{_e(commit_id[:SHORT_ID_LENGTH])}</code></a>'


def _references(model: dict[str, Any], commit: dict[str, Any]) -> tuple[list[str], list[str]]:
    branches = [
        branch["name"]
        for branch in model["branches"]
        if branch["commit_id"] == commit["id"] and not branch["deleted"]
    ]
    tags = [tag["name"] for tag in model["tags"] if tag["commit_id"] == commit["id"]]
    return branches, tags


def _branch_text(model: dict[str, Any], commit: dict[str, Any]) -> str:
    branch = model["branches_by_id"].get(commit["branch_id"])
    text = _e(commit["branch_name"])
    if branch is not None and branch["deleted"]:
        text += ' <span class="deleted">(削除済みブランチ)</span>'
    elif branch is not None and branch["name"] != commit["branch_name"]:
        text += f" (現在の名前: {_e(branch['name'])})"
    return text


def render_index(model: dict[str, Any]) -> str:
    repository = model["repository"]
    rows = []
    for commit in model["commits"]:
        branches, tags = _references(model, commit)
        note = f'<div class="note">{_e(commit["note"])}</div>' if commit["note"] is not None else ""
        children = ", ".join(_commit_link(model, "", child) for child in commit["children_ids"])
        rows.append(
            f'<tr id="c-{_e(commit["id"])}">'
            f"<td>{_e(commit['created_at'])}</td>"
            f"<td>{_commit_link(model, '', commit['id'])}<br><small><code>{_e(commit['id'])}</code></small></td>"
            f"<td>{_e(commit['message'])}{note}</td>"
            f"<td>{_branch_text(model, commit)}<br>{_chips(branches, 'branch')}</td>"
            f"<td>{_chips(tags, 'tag')}</td>"
            f"<td>{_chips(commit['labels'], 'label')}</td>"
            f"<td>{_commit_link(model, '', commit['parent_id'])}</td>"
            f"<td>{children or '(なし)'}</td>"
            f"<td>{len(commit['files'])}</td>"
            "</tr>"
        )
    branch_rows = "".join(
        f"<tr><td>{_e(branch['name'])}</td><td><code>{_e(branch['id'])}</code></td>"
        f"<td>{_commit_link(model, '', branch['commit_id'])}</td>"
        f"<td>{'削除済み' if branch['deleted'] else ('現在' if branch['id'] == model['current_branch_id'] else '')}</td>"
        f"<td>{_e(branch['comment'])}</td></tr>"
        for branch in model["branches"]
    )
    tag_rows = "".join(
        f"<tr><td>{_e(tag['name'])}</td><td>{_commit_link(model, '', tag['commit_id'])}</td>"
        f"<td>{_e(tag['created_at'])}</td><td>{_e(tag['comment'])}</td></tr>"
        for tag in model["tags"]
    )
    body = f"""<h1>Sprout アーカイブ</h1>
<p>リポジトリID: <code>{_e(repository['repository_id'])}</code><br>
リポジトリ作成日時: {_e(repository['repository_created_at'])}<br>
アーカイブ作成日時: {_e(model['generated_at'])}<br>
コミット数: {len(model['commits'])}<br>
機械可読な情報: <a href="archive.json">archive.json</a> / 説明: <a href="README.txt">README.txt</a></p>
<h2>コミット（新しい順）</h2>
<table>
<tr><th>日時 (UTC)</th><th>ID</th><th>メッセージ / メモ</th><th>ブランチ</th><th>タグ</th><th>ラベル</th><th>親</th><th>子</th><th>ファイル数</th></tr>
{''.join(rows)}
</table>
<h2>ブランチ</h2>
<table><tr><th>名前</th><th>ID</th><th>先端</th><th>状態</th><th>コメント</th></tr>{branch_rows}</table>
<h2>タグ</h2>
<table><tr><th>名前</th><th>コミット</th><th>作成日時</th><th>コメント</th></tr>{tag_rows}</table>"""
    return _page("Sprout アーカイブ", body)


def _attachment_html(from_dir: str, attachment: dict[str, Any], css_class: str) -> str:
    href = _href(from_dir, attachment["archive_path"])
    media_type = attachment["media_type"]
    name = _e(attachment.get("display_name") or attachment["original_name"])
    if media_type.startswith("image/"):
        player = f'<img src="{href}" alt="{name}">'
    elif media_type.startswith("audio/"):
        player = f'<audio controls preload="none" src="{href}"></audio>'
    elif media_type.startswith("video/"):
        player = f'<video controls preload="metadata" src="{href}"></video>'
    else:
        player = ""
    position = (
        f"表示順 {attachment['position'] + 1} / " if attachment["role"] == "preview" else ""
    )
    metadata = ('<strong>代表preview</strong>' if attachment.get('is_primary') else '')
    if attachment.get('description'):
        metadata += '<p>' + _e(attachment['description']).replace('\n', '<br>') + '</p>'
    if attachment.get('file_ids'):
        metadata += '<p>対象素材: ' + ', '.join(_e(value) for value in attachment['file_ids']) + '</p>'
    return (
        f'<div class="{css_class}" id="a-{_e(attachment["id"])}">'
        f"<div>{position}<a href=\"{href}\">{name}</a> "
        f"<small>({_e(media_type)}, {attachment['size']} bytes, ID <code>{_e(attachment['id'])}</code>)</small></div>"
        f"{metadata}{player}</div>"
    )


def render_commit(model: dict[str, Any], commit: dict[str, Any]) -> str:
    directory = commit["directory"]
    branches, tags = _references(model, commit)
    children = ", ".join(_commit_link(model, directory, child) for child in commit["children_ids"])
    file_rows = "".join(
        f'<tr><td><a href="{_href(directory, item["archive_path"])}">{_e(item["path"])}</a></td>'
        f"<td>{item['size']}</td><td><code>{_e(item['sha256'])}</code></td></tr>"
        for item in commit["files"]
    )
    thumbnail = (
        _attachment_html(directory, commit["thumbnail"], "thumbnail")
        if commit["thumbnail"] is not None
        else "<p>(なし)</p>"
    )
    previews = "".join(
        _attachment_html(directory, preview, "preview") for preview in commit["previews"]
    ) or "<p>(なし)</p>"
    note = (
        f'<div class="note">{_e(commit["note"])}</div><p><small>更新: {_e(commit["note_updated_at"])}</small></p>'
        if commit["note"] is not None
        else "<p>(なし)</p>"
    )
    index_href = _href(directory, "index.html")
    body = f"""<p><a href="{index_href}#c-{_e(commit['id'])}">← 全コミット一覧</a></p>
<h1>{_e(commit['message'])}</h1>
<table>
<tr><th>コミットID</th><td><code>{_e(commit['id'])}</code></td></tr>
<tr><th>日時 (UTC)</th><td>{_e(commit['created_at'])}</td></tr>
<tr><th>作成時のブランチ</th><td>{_branch_text(model, commit)} <small>ID <code>{_e(commit['branch_id'])}</code></small></td></tr>
<tr><th>このコミットを指すブランチ</th><td>{_chips(branches, 'branch') or '(なし)'}</td></tr>
<tr><th>タグ</th><td>{_chips(tags, 'tag') or '(なし)'}</td></tr>
<tr><th>ラベル</th><td>{_chips(commit['labels'], 'label') or '(なし)'}</td></tr>
<tr><th>親</th><td>{_commit_link(model, directory, commit['parent_id'])}</td></tr>
<tr><th>子</th><td>{children or '(なし)'}</td></tr>
<tr><th>メタデータ</th><td><a href="commit.json">commit.json</a> / <a href="files/">files/</a></td></tr>
</table>
<h2>メモ</h2>
{note}
<h2>サムネイル</h2>
{thumbnail}
<h2>preview（保存された表示順）</h2>
{previews}
<h2>ファイル ({len(commit['files'])})</h2>
<table><tr><th>パス</th><th>サイズ (bytes)</th><th>SHA-256</th></tr>{file_rows}</table>"""
    return _page(f"{commit['message']} - {commit['id'][:SHORT_ID_LENGTH]}", body)


def render_readme(model: dict[str, Any]) -> str:
    repository = model["repository"]
    return f"""Sprout static archive (format {ARCHIVE_FORMAT} version {ARCHIVE_FORMAT_VERSION})

repository_id: {repository['repository_id']}
repository_created_at: {repository['repository_created_at']}
generated_at: {model['generated_at']}
commits: {len(model['commits'])}

Open index.html in a web browser. No server, Sprout or Python is needed.

index.html      All commits with parents, children, branches, tags, labels and notes.
archive.json    Machine-readable metadata for every commit, file and attachment.
snapshots/<UTC time>_<short commit ID>/
  index.html    One commit: metadata, thumbnail, previews in stored order, file list.
  commit.json   The same commit entry as in archive.json.
  files/        The committed files at their relative paths.
  attachments/thumbnail/<attachment ID>/<original name>
  attachments/previews/<NNN>_<attachment ID>/<original name>

Not preserved (Sprout does not store them): empty directories, permissions,
owners, symbolic links and other file system metadata.
"""
