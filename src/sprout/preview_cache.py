"""Disposable, bounded per-project preview results; never a history dependency."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import struct
import tempfile
from contextlib import contextmanager

from .errors import SproutError

CACHE_LIMIT_BYTES = 256 * 1024 * 1024
ENTRY_LIMIT_BYTES = 32 * 1024 * 1024
ENTRY_NAME = re.compile(r'[0-9a-f]{64}\.json')


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()


def _read(repository, directory, key, identity):
    path = repository._restore_internal(directory / (key + '.json'))
    if not path.is_file() or path.stat().st_size > min(ENTRY_LIMIT_BYTES, CACHE_LIMIT_BYTES):
        return None
    try:
        payload = json.loads(path.read_bytes())
        value = payload['value']
        if payload['key'] != key or payload['checksum'] != hashlib.sha256(_canonical(value)).hexdigest():
            return None
        if not isinstance(value, dict) or value.get('format') not in identity['limits'][3]:
            return None
        if any(type(value.get(field)) is not int or not 1 <= value[field] <= limit
               for field,limit in [('width',identity['limits'][2]),('height',identity['limits'][2]),('display_width',identity['display_side']),('display_height',identity['display_side'])]):
            return None
        url = value.get('data_url')
        if not isinstance(url, str) or not url.startswith('data:image/png;base64,'):
            return None
        png = base64.b64decode(url.split(',',1)[1], validate=True)
        if (len(png)<24 or not png.startswith(b'\x89PNG\r\n\x1a\n') or png[12:16]!=b'IHDR'
                or struct.unpack('>II',png[16:24]) != (value['display_width'],value['display_height'])
                or value['width']*value['height']>identity['limits'][1]):
            return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    try:
        repository._restore_internal(path)
        if os.utime in os.supports_follow_symlinks:
            os.utime(path, follow_symlinks=False)
        else:
            os.utime(path)
    except (OSError, NotImplementedError):
        pass
    return value


@contextmanager
def _writer(repository, directory):
    path = repository._restore_internal(directory / 'cache.lock')
    with path.open('a+b') as handle:
        handle.seek(0, os.SEEK_END)
        if not handle.tell():
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _prune(repository, directory, budget, exclude):
    files = []
    for path in directory.iterdir():
        try:
            repository._restore_internal(path)
            if not path.is_file():
                continue
            info = path.stat()
            if ENTRY_NAME.fullmatch(path.name) and path.name != exclude:
                files.append((info.st_mtime_ns, path, info.st_size))
            elif path.name.startswith('pending-') and path.suffix == '.json':
                path.unlink()  # The exclusive writer lock proves no other writer is active.
        except (OSError, SproutError):
            continue
    total = sum(size for _,_,size in files)
    for _,path,size in sorted(files):
        if total <= budget:
            break
        try:
            path.unlink(); total -= size
        except OSError:
            pass
    return total <= budget


def _store(repository, directory, key, value):
    data = _canonical({'key': key, 'value': value,
                       'checksum': hashlib.sha256(_canonical(value)).hexdigest()})
    if len(data)>min(ENTRY_LIMIT_BYTES,CACHE_LIMIT_BYTES):
        _prune(repository,directory,max(0,CACHE_LIMIT_BYTES),'')
        return
    if not _prune(repository,directory,CACHE_LIMIT_BYTES-len(data),key+'.json'):
        return
    temporary = None
    try:
        fd,name = tempfile.mkstemp(prefix='pending-',suffix='.json',dir=directory)
        temporary = repository._restore_internal(directory / os.path.basename(name))
        with os.fdopen(fd,'wb') as file:
            file.write(data); file.flush(); os.fsync(file.fileno())
        os.replace(temporary, repository._restore_internal(directory/(key+'.json')))
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def get_or_render(repository, identity, render):
    """A cache failure must never turn a valid original into an unreadable preview."""
    key = hashlib.sha256(_canonical(identity)).hexdigest()
    directory = repository.control/'preview-cache'
    try:
        repository._restore_internal(directory)
        if directory.is_dir():
            cached = _read(repository,directory,key,identity)
            if cached is not None:
                try:
                    with _writer(repository,directory) as acquired:
                        if acquired:
                            _prune(repository,directory,max(0,CACHE_LIMIT_BYTES),'')
                except (OSError, SproutError):
                    pass
                return cached
    except (OSError, ValueError, SproutError):
        pass
    value = render()  # Original validation/decode failures remain user-facing errors.
    try:
        repository._restore_internal(directory)
        directory.mkdir(exist_ok=True)
        with _writer(repository,directory) as acquired:
            if acquired:
                _store(repository,directory,key,value)
    except (OSError, ValueError, SproutError):
        pass
    return value
