import io
import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from sprout.cli import app
from sprout.errors import SproutError
from sprout.repository import COVER_SIDE, Repository


def png(path: Path, size=(1200, 800), color=(10, 120, 200), mode='RGB') -> None:
    Image.new(mode, size, color).save(path, format='PNG')


def project(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    poster = repo.root / 'poster.png'
    png(poster)
    notes = repo.root / 'notes.txt'
    notes.write_text('text', encoding='utf-8')
    repo.track([poster, notes])
    return repo, poster, notes


def thumbnail_image(repo, commit):
    attachment = repo.thumbnail(commit)
    assert attachment is not None
    output = repo.root.parent / f'thumb-{attachment.id}'
    repo.export_thumbnail(commit, output, force=True)
    return attachment, Image.open(io.BytesIO(output.read_bytes()))


def test_save_makes_a_bounded_thumbnail_from_the_cover(tmp_path):
    repo, _, _ = project(tmp_path)
    assert repo.cover_file() == (None, None)
    file_id, relative, problem = repo.set_cover(repo.root / 'poster.png')
    assert (relative, problem) == ('poster.png', None)
    assert repo.cover_file() == (file_id, 'poster.png')

    result = repo.commit('first')

    assert result.cover.applied and result.cover.reason is None
    attachment, image = thumbnail_image(repo, result.commit_id)
    assert attachment.media_type == 'image/jpeg' and attachment.original_name == 'poster.jpg'
    assert max(image.size) == COVER_SIDE and image.size[0] / image.size[1] == pytest.approx(1.5, abs=0.01)
    assert repo.doctor().ok


def test_transparent_cover_stays_transparent(tmp_path):
    repo, poster, _ = project(tmp_path)
    png(poster, (64, 64), (1, 2, 3, 0), 'RGBA')
    repo.set_cover(poster)
    attachment, image = thumbnail_image(repo, repo.commit('first').commit_id)
    assert attachment.media_type == 'image/png'
    assert image.convert('RGBA').getpixel((0, 0))[3] == 0


@pytest.mark.parametrize('value', [0, 1, 255, 256, 30000, 32768, 65535])
@pytest.mark.parametrize('size', [(64, 64), (1024, 768)])
def test_16_bit_grayscale_cover_preserves_brightness(tmp_path, value, size):
    repo, poster, _ = project(tmp_path)
    png(poster, size, value, 'I;16')
    assert repo.set_cover(poster)[2] is None

    result = repo.commit('16-bit grayscale')

    assert result.cover.applied and result.cover.reason is None
    attachment, image = thumbnail_image(repo, result.commit_id)
    expected = round(value * 255 / 65535)
    assert attachment.media_type == 'image/jpeg'
    assert image.convert('RGB').getpixel((0, 0)) == pytest.approx((expected,) * 3, abs=1)
    assert max(image.size) == min(max(size), COVER_SIDE)


def test_16_bit_cover_preserves_tonal_range_when_resized(tmp_path):
    repo, poster, _ = project(tmp_path)
    source = Image.new('I;16', (1200, 800))
    for index, value in enumerate([0, 30000, 65535]):
        source.paste(Image.new('I;16', (400, 800), value), (index * 400, 0))
    source.save(poster, format='PNG')
    repo.set_cover(poster)

    _, image = thumbnail_image(repo, repo.commit('tonal range').commit_id)

    for fraction, expected in [(1 / 6, 0), (1 / 2, 117), (5 / 6, 255)]:
        assert image.convert('RGB').getpixel((int(image.width * fraction), image.height // 2)) == pytest.approx(
            (expected,) * 3, abs=1,
        )


def test_apply_16_bit_cover_uses_each_leafs_original_brightness(tmp_path):
    repo, poster, _ = project(tmp_path)
    png(poster, (800, 600), 30000, 'I;16')
    middle = repo.commit('middle gray').commit_id
    png(poster, (64, 64), 65535, 'I;16')
    white = repo.commit('white').commit_id
    png(poster, (64, 64), 0, 'I;16')
    repo.set_cover(poster)

    assert repo.apply_cover(dry_run=True)['applied'] == [middle, white]
    assert repo.thumbnail(middle) is None
    assert repo.apply_cover()['applied'] == [middle, white]
    for commit, expected in [(middle, 117), (white, 255)]:
        _, image = thumbnail_image(repo, commit)
        assert image.convert('RGB').getpixel((0, 0)) == pytest.approx((expected,) * 3, abs=1)
    assert repo.doctor().ok


@pytest.mark.parametrize('mode,format,color,expected', [
    ('RGB', 'PNG', (10, 120, 200), (10, 120, 200, 255)),
    ('RGBA', 'PNG', (10, 120, 200, 123), (10, 120, 200, 123)),
    ('LA', 'PNG', (120, 123), (120, 120, 120, 123)),
    ('P', 'PNG', 1, (10, 120, 200, 255)),
    ('L', 'PNG', 120, (120, 120, 120, 255)),
    ('1', 'PNG', 1, (255, 255, 255, 255)),
    ('CMYK', 'JPEG', (0, 128, 255, 0), (255, 127, 0, 255)),
    ('RGB', 'WEBP', (10, 120, 200), (10, 120, 200, 255)),
    ('RGB', 'BMP', (10, 120, 200), (10, 120, 200, 255)),
])
def test_cover_keeps_supported_formats_colors(tmp_path, mode, format, color, expected):
    repo, poster, _ = project(tmp_path)
    source = Image.new(mode, (64, 64), color)
    if mode == 'P':
        source.putpalette([0, 0, 0, 10, 120, 200] + [0] * (256 * 3 - 6))
    source.save(poster, format=format, **({'lossless': True} if format == 'WEBP' else {}))
    assert repo.set_cover(poster)[2] is None

    result = repo.commit('supported image')

    assert result.cover.applied
    _, image = thumbnail_image(repo, result.commit_id)
    assert image.convert('RGBA').getpixel((0, 0)) == pytest.approx(expected, abs=2)


def test_cover_conversion_failure_is_reported_without_a_thumbnail(tmp_path, monkeypatch):
    repo, poster, _ = project(tmp_path)
    png(poster, (64, 64), 30000, 'I;16')
    repo.set_cover(poster)
    convert = Image.Image.convert

    def fail_integer_conversion(image, *args, **kwargs):
        if image.mode == 'I;16':
            raise ValueError('cannot convert this image')
        return convert(image, *args, **kwargs)

    monkeypatch.setattr(Image.Image, 'convert', fail_integer_conversion)
    result = repo.commit('saved without thumbnail')
    assert (result.cover.applied, result.cover.reason) == (False, 'cover_unreadable')
    assert repo.thumbnail(result.commit_id) is None


def test_explicit_thumbnail_wins(tmp_path):
    repo, poster, _ = project(tmp_path)
    repo.set_cover(poster)
    manual = tmp_path / 'manual.png'
    png(manual, (10, 10))
    result = repo.commit('first', thumbnail=manual)
    assert result.cover is None
    assert repo.thumbnail(result.commit_id).original_name == 'manual.png'


def test_no_cover_means_no_thumbnail_and_no_report(tmp_path):
    repo, _, _ = project(tmp_path)
    result = repo.commit('first')
    assert result.cover is None and repo.thumbnail(result.commit_id) is None


def test_cover_follows_a_move_and_a_spelling_change(tmp_path, monkeypatch):
    repo, poster, _ = project(tmp_path)
    file_id = repo.set_cover(poster)[0]
    monkeypatch.chdir(repo.root)
    repo.move(Path('poster.png'), Path('art/final.png'))
    assert repo.cover_file() == (file_id, 'art/final.png')
    result = repo.commit('moved')
    assert result.cover.applied
    assert repo.thumbnail(result.commit_id).original_name == 'final.jpg'
    repo.move(Path('art/final.png'), Path('art/FINAL.png'))
    assert repo.cover_file() == (file_id, 'art/FINAL.png')


@pytest.mark.parametrize('prepare,reason', [
    (lambda repo, poster: poster.write_bytes(b'not an image'), 'cover_not_image'),
    (lambda repo, poster: repo.untrack([poster]), 'cover_missing'),
    (lambda repo, poster: poster.unlink(), 'cover_missing'),
])
def test_save_succeeds_and_reports_why_there_is_no_thumbnail(tmp_path, prepare, reason):
    repo, poster, _ = project(tmp_path)
    repo.set_cover(poster)
    prepare(repo, poster)
    result = repo.commit('saved anyway')
    assert result.commit_id
    assert (result.cover.applied, result.cover.reason) == (False, reason)
    assert repo.thumbnail(result.commit_id) is None
    assert repo.doctor().ok


def test_animated_and_oversized_covers_are_refused(tmp_path, monkeypatch):
    repo, poster, _ = project(tmp_path)
    repo.set_cover(poster)
    frames = [Image.new('RGB', (32, 32), color) for color in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
    frames[0].save(poster, format='WEBP', save_all=True, append_images=frames[1:], duration=100, lossless=True)
    assert repo.commit('animated').cover.reason == 'cover_animated'

    monkeypatch.setattr('sprout.repository.COVER_MAX_PIXELS', 10)
    png(poster, (8, 8))
    assert repo.commit('too many pixels').cover.reason == 'cover_too_large'
    monkeypatch.setattr('sprout.repository.COVER_MAX_BYTES', 1)
    png(poster, (9, 9))
    assert repo.commit('too many bytes').cover.reason == 'cover_too_large'


def test_setting_needs_a_tracked_file_and_warns_about_non_images(tmp_path):
    repo, _, notes = project(tmp_path)
    other = repo.root / 'other.png'
    png(other, (8, 8))
    with pytest.raises(SproutError) as error:
        repo.set_cover(other)
    assert error.value.code == 'cover_not_tracked'
    assert repo.cover_file() == (None, None)
    assert repo.set_cover(notes)[2] == 'cover_not_image'


def test_clear_stops_generation(tmp_path):
    repo, poster, _ = project(tmp_path)
    repo.set_cover(poster)
    repo.clear_cover()
    assert repo.cover_file() == (None, None)
    assert repo.thumbnail(repo.commit('first').commit_id) is None


def test_apply_fills_only_missing_thumbnails(tmp_path):
    repo, poster, notes = project(tmp_path)
    manual = tmp_path / 'manual.png'
    png(manual, (10, 10))
    without = repo.commit('without').commit_id
    notes.write_text('more', encoding='utf-8')
    kept = repo.commit('manual', thumbnail=manual).commit_id
    repo.set_cover(poster)

    plan = repo.apply_cover(dry_run=True)
    assert plan == {'dry_run': True, 'applied': [without], 'skipped': [], 'kept': 1}
    assert repo.thumbnail(without) is None
    assert repo.gc(dry_run=True).removed_objects == 0, 'a dry run stores nothing'

    assert repo.apply_cover()['applied'] == [without]
    assert repo.thumbnail(without).original_name == 'poster.jpg'
    assert repo.thumbnail(kept).original_name == 'manual.png'
    assert repo.apply_cover()['applied'] == []
    assert repo.doctor().ok


def test_apply_skips_leaves_without_the_file_or_an_image(tmp_path):
    repo, poster, notes = project(tmp_path)
    repo.untrack([poster])
    before = repo.commit('before the cover').commit_id
    repo.track([poster])
    with_image = repo.commit('with image').commit_id
    poster.write_bytes(b'broken')
    broken = repo.commit('broken').commit_id
    repo.set_cover(poster)
    result = repo.apply_cover()
    assert result['applied'] == [with_image]
    assert {(item['commit_id'], item['reason']) for item in result['skipped']} == {
        (before, 'cover_missing'), (broken, 'cover_not_image'),
    }


def test_apply_without_a_cover_is_refused(tmp_path):
    repo, _, _ = project(tmp_path)
    with pytest.raises(SproutError) as error:
        repo.apply_cover()
    assert error.value.code == 'cover_not_set'


def test_doctor_reports_an_unknown_cover(tmp_path):
    repo, _, _ = project(tmp_path)
    with repo.connect() as db:
        db.execute("INSERT INTO meta(key, value) VALUES('cover_file_id', 'missing')")
    assert 'invalid_cover' in {issue.kind for issue in repo.doctor().issues}


def test_cli_and_json(tmp_path, monkeypatch):
    repo, poster, _ = project(tmp_path)
    monkeypatch.chdir(repo.root)
    runner = CliRunner()
    assert 'No thumbnail source' in runner.invoke(app, ['leaf', 'thumbnail', 'source', 'show']).stdout
    status = json.loads(runner.invoke(app, ['status', '--tracked', '--json']).stdout)
    assert 'cover' not in status

    chosen = json.loads(runner.invoke(app, ['leaf', 'thumbnail', 'source', 'set', 'poster.png', '--json']).stdout)
    assert chosen['path'] == 'poster.png' and chosen['problem'] is None
    assert json.loads(runner.invoke(app, ['status', '--tracked', '--json']).stdout)['cover']['path'] == 'poster.png'

    saved = json.loads(runner.invoke(app, ['commit', '-m', 'first', '--json']).stdout)
    assert saved['cover'] == {'applied': True, 'reason': None}
    tree = json.loads(runner.invoke(app, ['tree', '--json']).stdout)
    assert tree['commits'][0]['attachments'][0]['role'] == 'thumbnail'

    poster.write_bytes(b'broken')
    warned = runner.invoke(app, ['commit', '-m', 'second'])
    assert warned.exit_code == 0
    assert 'cover_not_image' in warned.stderr

    assert json.loads(runner.invoke(app, ['leaf', 'thumbnail', 'source', 'apply', '--dry-run', '--json']).stdout)['dry_run'] is True
    before = repo.cover_file()
    for args in (['leaf', 'thumbnail', 'source', 'set', 'poster.png', '--clear'],
                 ['leaf', 'thumbnail', 'source', 'show', '--dry-run']):
        assert runner.invoke(app, args).exit_code != 0
        assert repo.cover_file() == before
    assert json.loads(runner.invoke(app, ['leaf', 'thumbnail', 'source', 'clear', '--json']).stdout)['file_id'] is None
