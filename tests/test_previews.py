import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from sprout import repository as repository_module
from sprout.cli import app
from sprout.errors import SproutError
from sprout.repository import PREVIEW_DEFAULT_MEDIA_TYPE, Repository

runner = CliRunner()


def committed_repo(tmp_path):
    repo = Repository.init(tmp_path / "project")
    asset = repo.root / "asset.bin"
    asset.write_bytes(b"base")
    repo.track([asset])
    commit = repo.commit("base").commit_id
    return repo, asset, commit


def write(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def snapshot(repo: Repository, commit: str):
    return [
        (item.id, item.position, item.original_name, item.media_type, item.object_hash, item.updated_at)
        for item in repo.previews(commit)
    ]


def test_previews_accept_any_format_and_keep_metadata(tmp_path):
    repo, _, commit = committed_repo(tmp_path)
    image = tmp_path / "in" / "still.png"
    image.parent.mkdir()
    Image.new("RGB", (8000, 8000), "red").save(image)
    sources = [
        image,
        write(tmp_path / "in" / "voice.wav", b"RIFF....WAVE"),
        write(tmp_path / "in" / "clip.mp4", b"\x00\x00\x00\x18ftypmp42"),
        write(tmp_path / "in" / "model.stl", b"solid cube\nendsolid"),
        write(tmp_path / "in" / "notes.pdf", b"%PDF-1.7"),
        write(tmp_path / "in" / "blob.unknownext", b"\x00\xffbinary"),
        write(tmp_path / "in" / "noextension", b"raw"),
    ]
    added = repo.add_previews(commit, sources)
    assert [item.original_name for item in added] == [source.name for source in sources]
    assert [item.position for item in added] == list(range(len(sources)))
    assert {item.role for item in added} == {"preview"}
    assert added[0].media_type == "image/png"
    assert added[2].media_type == "video/mp4"
    assert added[4].media_type == "application/pdf"
    assert added[6].media_type == PREVIEW_DEFAULT_MEDIA_TYPE
    for item, source in zip(added, sources):
        assert item.size == source.stat().st_size
        assert item.created_at == item.updated_at
        assert len(item.id) == 32
    custom = repo.add_previews(
        commit, [sources[5]], media_type="Application/X-Future-Format"
    )
    assert custom[0].media_type == "application/x-future-format"
    with pytest.raises(SproutError, match="invalid media type"):
        repo.add_previews(commit, [sources[5]], media_type="not a type")


def test_preview_objects_share_dedup_and_survive_gc(tmp_path):
    repo, asset, commit = committed_repo(tmp_path)
    same_as_file = write(tmp_path / "copy.bin", asset.read_bytes())
    first, second = repo.add_previews(commit, [same_as_file, same_as_file])
    assert first.id != second.id
    with repo.connect() as db:
        file_hash = db.execute(
            "SELECT object_hash FROM commit_files WHERE commit_id=?", (commit,)
        ).fetchone()[0]
        objects = db.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
    assert first.object_hash == second.object_hash == file_hash
    assert objects == 1
    only_preview = write(tmp_path / "only.dat", b"preview only")
    (stored,) = repo.add_previews(commit, [only_preview])
    assert stored.object_hash not in repo.gc(dry_run=True).objects
    assert repo.doctor().ok


def test_same_name_previews_are_operated_by_id(tmp_path):
    repo, _, commit = committed_repo(tmp_path)
    a = write(tmp_path / "a" / "take.wav", b"first")
    b = write(tmp_path / "b" / "take.wav", b"second")
    c = write(tmp_path / "c" / "take.wav", b"third")
    first, second, third = repo.add_previews(commit, [a, b, c])
    assert {item.original_name for item in (first, second, third)} == {"take.wav"}

    replacement = write(tmp_path / "new" / "take.wav", b"second v2")
    replaced = repo.replace_preview(commit, second.id[:8], replacement)
    assert replaced.id == second.id
    assert replaced.position == second.position
    assert replaced.created_at == second.created_at
    assert replaced.updated_at >= second.updated_at
    assert replaced.object_hash != second.object_hash
    previews = repo.previews(commit)
    assert [item.id for item in previews] == [first.id, second.id, third.id]
    assert previews[0] == first
    assert previews[2] == third

    deleted = repo.delete_preview(commit, first.id)
    assert deleted == first
    remaining = repo.previews(commit)
    assert [(item.id, item.position) for item in remaining] == [(second.id, 0), (third.id, 1)]
    assert remaining[1].object_hash == third.object_hash


def test_reorder_persists_after_reopen_in_every_view(tmp_path):
    repo, _, commit = committed_repo(tmp_path)
    sources = [write(tmp_path / f"p{index}.bin", bytes([index])) for index in range(3)]
    added = repo.add_previews(commit, sources)
    thumbnail = tmp_path / "thumb.png"
    Image.new("RGB", (2, 2), "blue").save(thumbnail)
    repo.set_thumbnail(commit, thumbnail)
    order = [added[2].id, added[0].id, added[1].id]
    reordered = repo.reorder_previews(commit, [item[:6] for item in order])
    assert [item.id for item in reordered] == order
    assert [item.position for item in reordered] == [0, 1, 2]

    reopened = Repository.discover(repo.root)
    assert [item.id for item in reopened.previews(commit)] == order
    attachments = reopened.attachments_many([commit])[commit]
    assert [item.id for item in attachments if item.role == "preview"] == order
    graph_attachments = reopened.commit_graph().commits[0].attachments
    assert [item.id for item in graph_attachments if item.role == "preview"] == order
    assert [item.created_at for item in reopened.previews(commit)] == [
        added[2].created_at,
        added[0].created_at,
        added[1].created_at,
    ]


def test_failed_preview_operations_change_nothing(tmp_path, monkeypatch):
    repo, asset, commit = committed_repo(tmp_path)
    sources = [write(tmp_path / f"p{index}.bin", bytes([index])) for index in range(2)]
    first, second = repo.add_previews(commit, sources)
    before = snapshot(repo, commit)

    with pytest.raises(SproutError, match="does not exist"):
        repo.add_previews(commit, [sources[0], tmp_path / "missing.bin"])
    with pytest.raises(SproutError, match="not a file"):
        repo.add_previews(commit, [tmp_path])
    with pytest.raises(SproutError, match="does not exist"):
        repo.replace_preview(commit, first.id, tmp_path / "missing.bin")
    with pytest.raises(SproutError) as unknown:
        repo.replace_preview(commit, "ffff", sources[0])
    assert unknown.value.code == "unknown_preview"
    with pytest.raises(SproutError) as unknown_delete:
        repo.delete_preview(commit, "ffff")
    assert unknown_delete.value.code == "unknown_preview"
    with pytest.raises(SproutError) as empty_id:
        repo.delete_preview(commit, "")
    assert empty_id.value.code == "unknown_preview"
    for invalid in ([first.id], [first.id, first.id], [first.id, second.id, "ffff"]):
        with pytest.raises(SproutError):
            repo.reorder_previews(commit, invalid)

    def broken_register(*_args, **_kwargs):
        raise SproutError("simulated failure")

    monkeypatch.setattr(repo, "_register_objects", broken_register)
    with pytest.raises(SproutError, match="simulated"):
        repo.add_previews(commit, [write(tmp_path / "new.bin", b"new")])
    with pytest.raises(SproutError, match="simulated"):
        repo.replace_preview(commit, first.id, write(tmp_path / "new2.bin", b"new2"))
    monkeypatch.undo()

    existing = write(tmp_path / "out" / "existing.bin", b"keep me")
    with pytest.raises(SproutError, match="already exists"):
        repo.export_preview(commit, first.id, existing)
    with pytest.raises(SproutError, match="tracked file"):
        repo.export_preview(commit, first.id, asset, force=True)
    with pytest.raises(SproutError, match="Sprout metadata"):
        repo.export_preview(commit, first.id, repo.control / "preview.bin")
    assert existing.read_bytes() == b"keep me"
    assert asset.read_bytes() == b"base"
    assert snapshot(Repository.discover(repo.root), commit) == before


def test_export_unknown_media_type_without_touching_worktree(tmp_path):
    repo, asset, commit = committed_repo(tmp_path)
    content = bytes(range(256)) * 10
    source = write(tmp_path / "data.zzz", content)
    (preview,) = repo.add_previews(commit, [source], media_type="application/x-unknown")
    status_before = repo.status()
    output = repo.export_preview(commit, preview.id, tmp_path / "exports" / "copy.zzz")
    assert output.read_bytes() == content
    inside = repo.export_preview(commit, preview.id, repo.root / "untracked-copy.zzz")
    assert inside.read_bytes() == content
    write(tmp_path / "exports" / "copy.zzz", b"old")
    repo.export_preview(commit, preview.id, tmp_path / "exports" / "copy.zzz", force=True)
    assert (tmp_path / "exports" / "copy.zzz").read_bytes() == content
    assert asset.read_bytes() == b"base"
    assert repo.status() == status_before


def test_large_previews_need_confirmation(tmp_path, monkeypatch):
    repo, _, commit = committed_repo(tmp_path)
    monkeypatch.setattr(repository_module, "PREVIEW_CONFIRM_BYTES", 4)
    small = write(tmp_path / "small.bin", b"1234")
    large = write(tmp_path / "large.bin", b"12345")
    plans = repo.plan_previews([small, large])
    assert [plan.requires_confirmation for plan in plans] == [False, True]
    assert [plan.additional_bytes for plan in plans] == [4, 5]
    assert not any(plan.already_stored for plan in plans)

    with pytest.raises(SproutError) as error:
        repo.add_previews(commit, [small, large])
    assert error.value.code == "preview_confirmation_required"
    assert error.value.details["size"] == 5
    assert repo.previews(commit) == []
    with repo.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM objects").fetchone()[0] == 1

    added = repo.add_previews(commit, [small, large], confirm_large=True)
    assert [item.size for item in added] == [4, 5]
    replanned = repo.plan_previews([large])
    assert replanned[0].already_stored
    assert replanned[0].additional_bytes == 0
    with pytest.raises(SproutError) as replace_error:
        repo.replace_preview(commit, added[0].id, large)
    assert replace_error.value.code == "preview_confirmation_required"
    assert repo.previews(commit)[0] == added[0]


def invoke(args, cwd: Path, monkeypatch):
    monkeypatch.chdir(cwd)
    return runner.invoke(app, args)


def test_preview_cli_workflow_and_json(tmp_path, monkeypatch):
    repo, _, commit = committed_repo(tmp_path)
    project = repo.root
    a = write(tmp_path / "a" / "same.mp3", b"aaa")
    b = write(tmp_path / "b" / "same.mp3", b"bbb")

    dry = invoke(['leaf', 'preview', 'add', commit, str(a), '--dry-run', '--json'], project, monkeypatch)
    assert dry.exit_code == 0
    assert json.loads(dry.stdout)["additional_bytes"] == 3
    assert repo.previews(commit) == []

    added = invoke(['leaf', 'preview', 'add', commit, str(a), str(b), '--json'], project, monkeypatch)
    assert added.exit_code == 0
    first, second = json.loads(added.stdout)
    assert first["original_name"] == second["original_name"] == "same.mp3"
    assert first["media_type"] == "audio/mpeg"
    assert {"id", "role", "position", "size", "created_at", "updated_at"} <= first.keys()

    ordered = invoke(['leaf', 'preview', 'order', commit, second["id"], first["id"], '--json'], project, monkeypatch)
    assert ordered.exit_code == 0
    assert [item["id"] for item in json.loads(ordered.stdout)] == [second["id"], first["id"]]

    listed = json.loads(invoke(['leaf', 'preview', 'list', commit, '--json'], project, monkeypatch).stdout)
    assert [(item["id"], item["position"]) for item in listed] == [(second["id"], 0), (first["id"], 1)]
    shown = json.loads(invoke(["show", commit, "--json"], project, monkeypatch).stdout)
    assert [item["id"] for item in shown["attachments"] if item["role"] == "preview"] == [second["id"], first["id"]]
    tree = json.loads(invoke(["tree", "--json"], project, monkeypatch).stdout)
    assert [item["id"] for item in tree["commits"][0]["attachments"]] == [second["id"], first["id"]]
    text = invoke(["show", commit], project, monkeypatch).stdout
    assert text.index(second["id"]) < text.index(first["id"])
    assert "[previews:2]" in invoke(["tree"], project, monkeypatch).stdout
    assert "1. " + second["id"] in invoke(['leaf', 'preview', 'list', commit], project, monkeypatch).stdout

    replacement = write(tmp_path / "c" / "other.ogg", b"ccc")
    replaced = json.loads(
        invoke(['leaf', 'preview', 'replace', commit, first["id"][:8], str(replacement), '--json'], project, monkeypatch).stdout
    )
    assert replaced["id"] == first["id"]
    assert replaced["original_name"] == "other.ogg"
    output = tmp_path / "exported.ogg"
    exported = invoke(['leaf', 'preview', 'export', commit, first["id"], '--output', str(output), '--json'], project, monkeypatch)
    assert exported.exit_code == 0
    assert output.read_bytes() == b"ccc"
    deleted = json.loads(invoke(['leaf', 'preview', 'delete', commit, second["id"], '--json'], project, monkeypatch).stdout)
    assert deleted["deleted"] is True
    assert [item.id for item in repo.previews(commit)] == [first["id"]]

    invalid = invoke(['leaf', 'preview', 'order', commit, 'ffff', '--json'], project, monkeypatch)
    assert invalid.exit_code != 0
    assert [item.id for item in repo.previews(commit)] == [first["id"]]


def test_preview_cli_large_file_requires_yes(tmp_path, monkeypatch):
    repo, _, commit = committed_repo(tmp_path)
    monkeypatch.setattr(repository_module, "PREVIEW_CONFIRM_BYTES", 2)
    large = write(tmp_path / "big.mov", b"12345")
    dry = invoke(['leaf', 'preview', 'add', commit, str(large), '--dry-run'], repo.root, monkeypatch)
    assert dry.exit_code == 0
    assert "needs --yes" in dry.stdout
    refused = invoke(['leaf', 'preview', 'add', commit, str(large)], repo.root, monkeypatch)
    assert refused.exit_code != 0
    assert repo.previews(commit) == []
    accepted = invoke(['leaf', 'preview', 'add', commit, str(large), '--yes'], repo.root, monkeypatch)
    assert accepted.exit_code == 0
    assert len(repo.previews(commit)) == 1


def test_static_image_preview_formats_are_read_only(tmp_path, monkeypatch):
    import base64
    import io
    from sprout.preview_image import render_preview_image

    repo, asset, commit = committed_repo(tmp_path)
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
    before = asset.read_bytes()
    for image_format, extension in [("PNG", "png"), ("JPEG", "jpg"), ("WEBP", "webp"), ("BMP", "bmp")]:
        source = tmp_path / f"image.{extension}"
        Image.new("RGB", (24, 12), "red").save(source, format=image_format)
        original = source.read_bytes()
        attachment = repo.add_previews(commit, [source])[0]
        saved = snapshot(repo, commit)
        result = render_preview_image(repo, commit, attachment.id)
        with Image.open(io.BytesIO(base64.b64decode(result["data_url"].split(",", 1)[1]))) as displayed:
            assert displayed.format == "PNG"
            assert displayed.size == (24, 12)
            red, green, blue, alpha = displayed.convert("RGBA").getpixel((0, 0))
            assert red > 200 and green < 10 and blue < 10 and alpha == 255
        assert result["width"] == 24
        assert result["height"] == 12
        assert snapshot(repo, commit) == saved
        assert source.read_bytes() == original
        assert asset.read_bytes() == before
        assert not list(tmp_path.glob("sprout-preview-image-*"))


def test_static_image_preview_resizes_without_changing_source(tmp_path):
    from sprout.preview_image import render_preview_image
    repo, _, commit = committed_repo(tmp_path)
    source = tmp_path / "large.png"
    Image.new("RGB", (3000, 1500), "green").save(source)
    attachment = repo.add_previews(commit, [source])[0]
    result = render_preview_image(repo, commit, attachment.id)
    assert (result["width"], result["height"]) == (3000, 1500)
    assert (result["display_width"], result["display_height"]) == (2048, 1024)
    with Image.open(source) as image:
        assert image.size == (3000, 1500)


@pytest.mark.parametrize("kind,code", [
    ("broken", "invalid_preview_image"),
    ("gif", "unsupported_preview_image"),
    ("animated", "animated_preview_image"),
    ("bytes", "preview_image_too_large"),
    ("pixels", "preview_image_too_large"),
])
def test_static_image_preview_errors_keep_attachments_and_cleanup(tmp_path, monkeypatch, kind, code):
    from sprout import preview_image
    repo, _, commit = committed_repo(tmp_path)
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
    source = tmp_path / "input.png"
    if kind == "broken":
        source.write_bytes(b"not an image")
    elif kind == "animated":
        Image.new("RGB", (4, 4), "red").save(source, save_all=True, append_images=[Image.new("RGB", (4, 4), "blue")])
    else:
        Image.new("RGB", (4, 4), "red").save(source, format="GIF" if kind == "gif" else "PNG")
    attachment = repo.add_previews(commit, [source])[0]
    saved = snapshot(repo, commit)
    if kind == "bytes": monkeypatch.setattr(preview_image, "MAX_IMAGE_BYTES", 1)
    if kind == "pixels": monkeypatch.setattr(preview_image, "MAX_IMAGE_PIXELS", 1)
    with pytest.raises(SproutError) as error:
        preview_image.render_preview_image(repo, commit, attachment.id)
    assert error.value.code == code
    assert snapshot(repo, commit) == saved
    assert not list(tmp_path.glob("sprout-preview-image-*"))


def test_static_image_preview_cli_returns_json(tmp_path, monkeypatch):
    repo, _, commit = committed_repo(tmp_path)
    source = tmp_path / "image.png"
    Image.new("RGB", (3, 2), "blue").save(source)
    attachment = repo.add_previews(commit, [source])[0]
    monkeypatch.chdir(repo.root)
    result = runner.invoke(app, ['leaf', 'preview', 'image', commit, attachment.id, '--json'])
    assert result.exit_code == 0, result.stdout
    reply = json.loads(result.stdout)
    assert reply["data_url"].startswith("data:image/png;base64,")
    assert (reply["width"], reply["height"]) == (3, 2)
