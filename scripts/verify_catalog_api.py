"""Recreate synthetic projects and verify API v1 through a real CLI executable.

Always creates a fresh run directory; never changes an existing project.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from PIL import Image
from sprout.repository import Repository


def verify(executable: Path, destination: Path) -> dict:
    executable = executable.resolve(strict=True)
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='run-', dir=destination.resolve()))
    records = []

    def run(cwd, *args, success=True, json_output=True):
        arguments = [str(executable), *map(str, args)] + (['--json'] if json_output else [])
        process = subprocess.run(arguments, cwd=cwd, capture_output=True,
                                 env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, timeout=60)
        stdout, stderr = process.stdout.decode('utf-8'), process.stderr.decode('utf-8')
        records.append({'cwd': str(cwd), 'arguments': arguments[1:], 'exit_code': process.returncode,
                        'stdout': stdout, 'stderr': stderr})
        assert (process.returncode == 0) == success, records[-1]
        if success:
            assert stderr == '', records[-1]
            return json.loads(stdout) if json_output else stdout.strip()
        assert stdout == '', records[-1]
        return json.loads(stderr)

    version = run(root, '--version', json_output=False)
    assert run(root, 'info', success=False)['code'] == 'not_initialized'
    assert run(root, 'catalog', success=False)['code'] == 'not_initialized'
    empty = root / '空 project'
    run(root, 'init', empty)
    empty_info = run(empty, 'info')
    assert run(empty, 'catalog') == {'api_version': 1, 'repository': empty_info['repository'], 'variants': []}

    project = root / '画像 project'
    run(root, 'init', project)
    asset = project / '資料 file.txt'
    dependency = project / 'textures' / '色 data.bin'
    dependency.parent.mkdir()
    dependency.write_bytes(b'synthetic dependency\x00\xff')
    image_expectations = {}
    for index, (fmt, suffix) in enumerate([('JPEG', 'jpg'), ('PNG', 'png'), ('WEBP', 'webp')]):
        image = root / f'preview {index}.{suffix}'
        Image.new('RGB', (24, 16), ['red', 'green', 'blue'][index]).save(image, format=fmt)
        asset.write_text(f'合成資料 {fmt}\n', encoding='utf-8')
        run(project, 'file', 'track', asset.name, str(dependency.relative_to(project)))
        result = run(project, 'leaf', 'create', '-m', f'{fmt} の版', '--thumbnail', image)
        commit = result['id']
        run(project, 'leaf', 'tag', 'create', f'版{index}', commit)
        image_expectations[commit] = image
    # Mutable metadata and multiple tags are visible without a new commit.
    run(project, 'leaf', 'tag', 'create', 'Alternate', commit)
    run(project, 'leaf', 'edit', commit, '--note', '確認 メモ AbC')
    run(project, 'leaf', 'label', 'add', commit, 'Approved')
    asset.write_text('未保存の作業を維持\n', encoding='utf-8')
    repository = Repository.discover(project)

    def state():
        with repository.connect() as db:
            database = list(db.iterdump())
        files = {str(p.relative_to(project)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                 for p in project.rglob('*') if p.is_file() and '.sprout' not in p.relative_to(project).parts}
        return database, files

    before = state()
    info, catalog = run(project, 'info'), run(project, 'catalog')
    assert info['repository'] == catalog['repository']
    assert len(catalog['variants']) == 3
    for variant in catalog['variants']:
        commit = variant['commit_id']
        shown = run(project, 'leaf', 'show', commit)
        assert shown['id'] == commit and len(shown['files']) == 2
        image = image_expectations[commit]
        thumbnail = root / f'export-{image.name}'
        run(project, 'leaf', 'thumbnail', 'export', commit, '--output', thumbnail)
        content = thumbnail.read_bytes()
        assert content == image.read_bytes()
        assert len(content) == variant['thumbnail']['size']
        assert hashlib.sha256(content).hexdigest() == variant['thumbnail']['object_hash']
        output = root / f'files-{commit}'
        exported = run(project, 'file', 'export', commit, '--output', output)
        assert set(exported) == {'commit_id', 'output', 'paths'}
        assert exported['commit_id'] == commit and exported['output'] == str(output)
        assert sorted(exported['paths']) == sorted(f['path'] for f in shown['files'])
        assert sorted(str(p.relative_to(output)).replace('\\', '/') for p in output.rglob('*') if p.is_file()) == sorted(exported['paths'])
        for file in shown['files']:
            content = (output / file['path']).read_bytes()
            assert len(content) == file['size']
            assert hashlib.sha256(content).hexdigest() == file['object_hash']
        run(project, 'file', 'export', commit, '--output', output, success=False)
    assert state() == before
    run(project, 'info', json_output=False)
    run(project, 'catalog', json_output=False)
    assert state() == before
    report = {'executable': str(executable), 'version': version, 'root': str(root),
              'project': str(project), 'empty_project': str(empty), 'variants': 3,
              'image_formats': ['JPEG', 'PNG', 'WEBP'], 'state_unchanged': True,
              'info': info, 'catalog': catalog, 'commands': records}
    (root / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('.test-tmp/catalog-api'))
    args = parser.parse_args()
    result = verify(args.executable, args.output)
    print(Path(result['root']) / 'verification.json')
