"""Atomic recovery records for explicitly supported destructive operations."""
from __future__ import annotations

import json
import uuid

from .errors import SproutError

TRASH_RECORD_VERSION = 1
BUD_KINDS = {'bud_delete', 'discard'}

# Ordered parents before dependents; identifiers below are never supplied by records.
KEYS = {
    'commits': ('id',), 'commit_files': ('commit_id', 'path'),
    'commit_attachments': ('id',), 'preview_assets': ('attachment_id','file_id'), 'commit_notes': ('commit_id',),
    'commit_labels': ('commit_id', 'label'), 'branches': ('id',),
    'repository_state': ('id',), 'buds': ('id',), 'bud_files': ('bud_id', 'path'),
}


def next_seq(db, name):
    """Allocate the next creation-order number; numbers are never reused."""
    db.execute('UPDATE id_sequences SET last_value=last_value+1 WHERE name=?', (name,))
    return db.execute('SELECT last_value FROM id_sequences WHERE name=?', (name,)).fetchone()[0]


def rows(db, table, where, args):
    return [dict(row) for row in db.execute(f'SELECT * FROM {table} WHERE {where}', args)]


def capture_commit(db, commit_id):
    result = {'commits': rows(db, 'commits', 'id=? OR parent_id=?', (commit_id, commit_id))}
    for table in ('commit_files', 'commit_attachments', 'preview_assets', 'commit_notes', 'commit_labels'):
        result[table] = rows(db, table, 'commit_id=?', (commit_id,))
    result['branches'] = rows(db, 'branches', 'commit_id=?', (commit_id,))
    result['buds'] = rows(db, 'buds', 'base_commit_id=?', (commit_id,))
    result['repository_state'] = rows(db, 'repository_state', 'current_commit_id=?', (commit_id,))
    return result


def capture_preview(db, commit_id):
    return {'commit_attachments': rows(db, 'commit_attachments',
                                     "commit_id=? AND role='preview'", (commit_id,)),
            'preview_assets': rows(db,'preview_assets','commit_id=?',(commit_id,))}


def capture_bud(db, bud_id):
    return {'buds': rows(db, 'buds', 'id=?', (bud_id,)),
            'bud_files': rows(db, 'bud_files', 'bud_id=?', (bud_id,))}


def current_row(db, table, original):
    key = KEYS[table]
    row = db.execute(f"SELECT * FROM {table} WHERE " + ' AND '.join(f'{k}=?' for k in key),
                     tuple(original[k] for k in key)).fetchone()
    return dict(row) if row else None


def record(db, before, kind, title, target_id, created_at, *, preview_commit=None):
    patches = []
    for table, originals in before.items():
        for original in originals:
            after = current_row(db, table, original)
            if original != after or table == 'preview_assets':
                patches.append({'table': table, 'before': original, 'after': after})
    if not patches:
        return None
    payload = {'version': TRASH_RECORD_VERSION, 'patches': patches}
    if preview_commit:
        payload.update(preview_commit=preview_commit,
                       preview_after=capture_preview(db, preview_commit)['commit_attachments'],
                       assets_after=capture_preview(db, preview_commit)['preview_assets'])
    item_id = uuid.uuid4().hex
    db.execute('INSERT INTO trash_entries(id,seq,kind,target_id,title,created_at,payload) VALUES(?,?,?,?,?,?,?)',
               (item_id, next_seq(db, 'trash_entries'), kind, target_id, title, created_at, json.dumps(payload, sort_keys=True)))
    objects = {(p['before']['object_hash'], p['before']['size']) for p in patches
               if p['table'] in {'commit_files', 'commit_attachments', 'bud_files'}}
    db.executemany('INSERT INTO trash_objects(trash_id,object_hash,size) VALUES(?,?,?)',
                   ((item_id, digest, size) for digest, size in sorted(objects)))
    return item_id


def load(db, item_id):
    row = db.execute('SELECT * FROM trash_entries WHERE id=?', (item_id,)).fetchone()
    if row is None:
        raise SproutError(f'unknown trash item: {item_id}', code='unknown_trash_item', details={'trash_id': item_id})
    return dict(row)


def validate(db, item):
    try:
        payload = json.loads(item['payload'])
        if (type(payload['version']) is not int or payload['version'] != TRASH_RECORD_VERSION
                or not isinstance(payload['patches'], list) or not payload['patches']):
            raise ValueError('unsupported or empty record')
        seen = set()
        for patch in payload['patches']:
            table, before, after = patch['table'], patch['before'], patch['after']
            if table not in KEYS or not isinstance(before, dict):
                raise ValueError('invalid table or row')
            columns = {r['name'] for r in db.execute(f'PRAGMA table_info({table})')}
            if set(before) != columns or (after is not None and (
                    not isinstance(after, dict) or set(after) != columns
                    or any(before[k] != after[k] for k in KEYS[table]))):
                raise ValueError('invalid row columns or identity')
            key = (table, *(before[k] for k in KEYS[table]))
            if key in seen:
                raise ValueError('duplicate row')
            seen.add(key)
        if item['kind'].startswith('preview') and 'preview_commit' not in payload:
            raise ValueError('missing preview context')
        if 'preview_commit' in payload:
            if not isinstance(payload['preview_commit'], str) or not isinstance(payload.get('preview_after'), list):
                raise ValueError('invalid preview context')
            if any(not isinstance(row, dict) or not isinstance(row.get('id'), str)
                   for row in payload['preview_after']):
                raise ValueError('invalid preview rows')
        if 'preview_commit' in payload:
            assets = payload.get('assets_after')
            columns = {r['name'] for r in db.execute('PRAGMA table_info(preview_assets)')}
            if not isinstance(assets, list) or any(
                not isinstance(row, dict) or set(row) != columns
                or not isinstance(row.get('attachment_id'), str) or not isinstance(row.get('file_id'), str)
                for row in assets
            ):
                raise ValueError('invalid preview material context')
        return payload
    except (ValueError, KeyError, TypeError) as exc:
        raise SproutError('invalid trash recovery record; retained without changes',
                          code='invalid_trash_record', details={'trash_id': item['id']}) from exc


def conflict(item_id, reason):
    raise SproutError(f'cannot restore trash item: {reason}; no changes applied',
                      code='trash_restore_conflict', details={'trash_id': item_id, 'reason': reason})


def restore(db, item):
    payload = validate(db, item)
    if 'preview_commit' in payload:
        commit_id = payload['preview_commit']
        if not db.execute('SELECT 1 FROM commits WHERE id=?', (commit_id,)).fetchone():
            conflict(item['id'], 'the containing commit is missing')
        actual = capture_preview(db, commit_id)['commit_attachments']
        ordered = lambda values: sorted(values, key=lambda r: r['id'])
        if ordered(actual) != ordered(payload.get('preview_after', [])):
            conflict(item['id'], 'the preview list changed; undo newer preview operations first')
    if 'preview_commit' in payload:
        assets = capture_preview(db, payload['preview_commit'])['preview_assets']
        if sorted(assets, key=lambda r:(r['attachment_id'],r['file_id'])) != sorted(payload.get('assets_after',[]), key=lambda r:(r['attachment_id'],r['file_id'])):
            conflict(item['id'], 'preview material associations changed')
    for patch in payload['patches']:
        if item['kind'] in BUD_KINDS and patch['table'] == 'buds':
            base = patch['before']['base_commit_id']
            if base is not None and not db.execute('SELECT 1 FROM commits WHERE id=?', (base,)).fetchone():
                conflict(item['id'], 'the snapshot this bud was kept on no longer exists')
        if current_row(db, patch['table'], patch['before']) != patch['after']:
            conflict(item['id'], f"{patch['table']} changed since this operation")
    db.execute('PRAGMA defer_foreign_keys=ON')
    # Attachment positions are unique at every statement, so remove all affected
    # rows first, then insert their original versions in the same transaction.
    for patch in payload['patches']:
        if patch['table'] == 'preview_assets' and patch['after'] is not None:
            db.execute('DELETE FROM preview_assets WHERE attachment_id=? AND file_id=?', (patch['after']['attachment_id'],patch['after']['file_id']))
        if patch['table'] == 'commit_attachments' and patch['after'] is not None:
            db.execute('DELETE FROM commit_attachments WHERE id=?', (patch['after']['id'],))
    for table in KEYS:
        for patch in payload['patches']:
            if patch['table'] != table:
                continue
            before = patch['before']
            if patch['after'] is None or table in {'commit_attachments','preview_assets'}:
                columns = list(before)
                db.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                           tuple(before[c] for c in columns))
            else:
                columns = [c for c in before if c not in KEYS[table]]
                db.execute(f"UPDATE {table} SET " + ','.join(f'{c}=?' for c in columns)
                           + ' WHERE ' + ' AND '.join(f'{k}=?' for k in KEYS[table]),
                           tuple(before[c] for c in columns) + tuple(before[k] for k in KEYS[table]))
    db.execute('DELETE FROM trash_entries WHERE id=?', (item['id'],))
