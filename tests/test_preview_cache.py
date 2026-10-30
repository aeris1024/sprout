import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from PIL import Image
from sprout.repository import Repository
from sprout import preview_cache as cache
from sprout import preview_image as viewer
from sprout.errors import SproutError


def setup(tmp_path, name='project'):
    repo=Repository.init(tmp_path/name)
    asset=repo.root/'asset'; asset.write_bytes(b'asset'); repo.track([asset])
    commit=repo.commit('base').commit_id
    source=tmp_path/(name+'.png'); Image.new('RGB',(32,16),'red').save(source)
    item=repo.add_previews(commit,[source])[0]
    return repo,commit,item,source


def render(repo,commit,item):
    return viewer.render_preview_image(repo,commit,item.id)


def entries(repo):
    return list((repo.control/'preview-cache').glob('*.json'))


def test_hit_skips_original_export_and_decode_and_returns_metadata(tmp_path,monkeypatch):
    repo,commit,item,source=setup(tmp_path)
    first=render(repo,commit,item)
    assert first['format']=='PNG' and first['width']==32 and first['height']==16
    def forbidden(*args,**kwargs): raise AssertionError('original should not be fetched or decoded')
    monkeypatch.setattr(viewer,'_render_uncached',forbidden)
    monkeypatch.setattr(repo,'export_preview',forbidden)
    assert render(repo,commit,item)==first


@pytest.mark.parametrize('condition',['processing','decoder','size','limit'])
def test_condition_changes_regenerate(tmp_path,monkeypatch,condition):
    repo,commit,item,source=setup(tmp_path)
    render(repo,commit,item)
    if condition=='processing': monkeypatch.setattr(viewer,'PROCESSING_VERSION',99)
    elif condition=='decoder': monkeypatch.setattr(viewer,'pillow_version','changed')
    elif condition=='size': monkeypatch.setattr(viewer,'DISPLAY_SIDE',8)
    else: monkeypatch.setattr(viewer,'MAX_IMAGE_SIDE',4096)
    calls=[]; original=viewer._render_uncached
    def count(*args): calls.append(1); return original(*args)
    monkeypatch.setattr(viewer,'_render_uncached',count)
    result=render(repo,commit,item)
    assert len(calls)==1
    assert render(repo,commit,item)==result and len(calls)==1
    assert len(entries(repo))==2
    if condition=='size': assert result['display_width']==8


def test_replacement_and_project_isolation(tmp_path,monkeypatch):
    repo,commit,item,source=setup(tmp_path)
    original=render(repo,commit,item)
    Image.new('RGB',(8,8),'blue').save(source)
    changed=repo.replace_preview(commit,item.id,source)
    result=render(repo,commit,changed)
    assert result['width']==8 and result['data_url']!=original['data_url']
    other,other_commit,other_item,_=setup(tmp_path,'other')
    calls=[]; decode=viewer._render_uncached
    def count(*args): calls.append(1); return decode(*args)
    monkeypatch.setattr(viewer,'_render_uncached',count)
    assert render(other,other_commit,other_item)==original
    assert calls==[1] and entries(other)


@pytest.mark.parametrize('damage',['truncated','metadata','png','deleted'])
def test_corruption_or_missing_cache_regenerates(tmp_path,damage):
    repo,commit,item,source=setup(tmp_path)
    expected=render(repo,commit,item); entry=entries(repo)[0]
    if damage=='deleted': entry.unlink()
    elif damage=='truncated': entry.write_bytes(b'{')
    else:
        payload=json.loads(entry.read_bytes())
        if damage=='metadata': payload['value']['width']=31
        else: payload['value']['data_url']='data:image/png;base64,AAAA'
        entry.write_text(json.dumps(payload))
    assert render(repo,commit,item)==expected
    assert json.loads(entries(repo)[0].read_bytes())['value']==expected


def test_storage_failure_and_invalid_cache_directory_fall_back(tmp_path,monkeypatch):
    repo,commit,item,source=setup(tmp_path)
    before=repo.manifest(commit)
    def failure(*args): raise OSError('cache cannot be saved')
    with monkeypatch.context() as context:
        context.setattr(cache,'_store',failure)
        result=render(repo,commit,item)
    directory=repo.control/'preview-cache'
    assert directory.resolve().parent==repo.control.resolve()
    shutil.rmtree(directory)
    directory.write_bytes(b'not a directory')
    assert render(repo,commit,item)==result
    directory.unlink()
    assert render(repo,commit,item)==result
    assert repo.manifest(commit)==before and repo.doctor().ok


def test_lru_limit_and_oversize_fallback(tmp_path,monkeypatch):
    repo,commit,item,source=setup(tmp_path)
    render(repo,commit,item)
    red=entries(repo)[0]
    Image.new('RGB',(32,16),'blue').save(source)
    blue=repo.add_previews(commit,[source])[0]; render(repo,commit,blue)
    old_entries=entries(repo)
    max_size=max(p.stat().st_size for p in old_entries)
    monkeypatch.setattr(cache,'CACHE_LIMIT_BYTES',2*max_size+32)
    for path in old_entries: os.utime(path,(1_600_000_000,1_600_000_000))
    render(repo,commit,item)  # Red is the most recently used entry.
    assert red.stat().st_mtime_ns > 1_600_000_000_000_000_000
    Image.new('RGB',(32,16),'green').save(source)
    green=repo.add_previews(commit,[source])[0]; render(repo,commit,green)
    assert red.exists() and len(entries(repo))==2
    assert sum(p.stat().st_size for p in entries(repo))<=cache.CACHE_LIMIT_BYTES
    monkeypatch.setattr(cache,'CACHE_LIMIT_BYTES',1)
    assert render(repo,commit,item)['width']==32
    assert entries(repo)==[]


def test_concurrent_generation_and_interruption_do_not_publish_partial_entries(tmp_path,monkeypatch):
    repo,commit,item,source=setup(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:render(repo,commit,item),range(2)))
    assert results[0]==results[1] and len(entries(repo))==1
    directory=repo.control/'preview-cache'
    assert directory.resolve().parent==repo.control.resolve()
    shutil.rmtree(directory)
    replace=cache.os.replace
    def interrupt(src,dst):
        if Path(src).name.startswith('pending-'): raise KeyboardInterrupt('interrupt cache publication')
        return replace(src,dst)
    with monkeypatch.context() as context:
        context.setattr(cache.os,'replace',interrupt)
        with pytest.raises(KeyboardInterrupt): render(repo,commit,item)
    assert not entries(repo) and not list(directory.glob('pending-*'))
    assert render(repo,commit,item)==results[0]
    assert repo.doctor().ok


def test_cache_does_not_bypass_original_encoding_or_missing_object_checks(tmp_path):
    repo,commit,item,source=setup(tmp_path)
    render(repo,commit,item)
    with repo.connect() as db: db.execute("UPDATE objects SET encoding='future' WHERE hash=?",(item.object_hash,))
    with pytest.raises(SproutError) as error: render(repo,commit,item)
    assert error.value.code=='unsupported_object_encoding'
    with repo.connect() as db: db.execute("UPDATE objects SET encoding='zstd' WHERE hash=?",(item.object_hash,))
    repo._object_path(item.object_hash).unlink()
    with pytest.raises(SproutError): render(repo,commit,item)


def test_abandoned_pending_files_are_cleaned_without_touching_history(tmp_path):
    repo,commit,item,source=setup(tmp_path)
    expected=render(repo,commit,item)
    abandoned=repo.control/'preview-cache'/'pending-abandoned.json'
    abandoned.write_bytes(b'incomplete')
    manifest=repo.manifest(commit)
    assert render(repo,commit,item)==expected
    assert not abandoned.exists()
    assert repo.manifest(commit)==manifest and repo.doctor().ok
