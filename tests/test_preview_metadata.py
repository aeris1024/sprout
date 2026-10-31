import json
import sqlite3
import pytest
from typer.testing import CliRunner
from sprout.cli import app
from sprout.errors import SproutError
from sprout.repository import Repository


def setup(tmp_path):
    repo=Repository.init(tmp_path/'project')
    a,b=repo.root/'a.bin',repo.root/'b.bin'
    a.write_bytes(b'same'); b.write_bytes(b'same')
    repo.track([a,b]); commit=repo.commit('base').commit_id
    source=tmp_path/'preview.wav'; source.write_bytes(b'preview')
    first,second=repo.add_previews(commit,[source,source])
    ids=[f.file_id for f in repo.manifest(commit).values()]
    return repo,commit,first,second,ids,source


def test_metadata_set_clear_and_archive(tmp_path,monkeypatch):
    repo,commit,first,second,ids,source=setup(tmp_path)
    changed=repo.set_preview_metadata(commit,first.id,display_name='  Cafe\u0301  ',description='first\nsecond',file_ids=ids)
    assert changed.display_name=='Café' and changed.description=='first\nsecond'
    assert changed.file_ids==tuple(sorted(ids))
    assert changed.original_name==first.original_name and changed.object_hash==first.object_hash
    monkeypatch.chdir(repo.root)
    output=CliRunner().invoke(app,['preview','metadata',commit,first.id,'--name=Review','--description=Notes','--file-id',ids[0],'--json'])
    assert output.exit_code==0,output.exception
    assert json.loads(output.stdout)['file_ids']==[ids[0]]
    assert 'is_primary' not in json.loads(output.stdout)
    archive=tmp_path/'archive'; repo.archive(archive)
    record=json.loads((archive/'archive.json').read_text(encoding='utf-8'))['commits'][0]
    assert record['previews'][0]['display_name']=='Review'
    assert 'is_primary' not in record['previews'][0]
    assert 'Review' in (archive/record['directory']/'index.html').read_text(encoding='utf-8')
    assert Repository.discover(repo.root).preview(commit,first.id).display_name=='Review'
    empty=repo.set_preview_metadata(commit,first.id,display_name='',description='',file_ids=[])
    assert not empty.display_name and not empty.description and not empty.file_ids


@pytest.mark.parametrize('options',[{'display_name':'x'*257},{'display_name':'bad\nname'},{'description':'x'*20001},{'file_ids':['f'*32]}])
def test_invalid_metadata_update_is_atomic(tmp_path,options):
    repo,commit,first,second,ids,source=setup(tmp_path)
    before=repo.previews(commit)
    with pytest.raises(SproutError):
        repo.set_preview_metadata(commit,first.id,**options)
    assert repo.previews(commit)==before


def test_cross_commit_reference_and_db_constraints(tmp_path):
    repo,commit,first,second,ids,source=setup(tmp_path)
    extra=repo.root/'extra'; extra.write_bytes(b'extra'); repo.track([extra])
    later=repo.commit('later').commit_id
    other=repo.manifest(later)['extra'].file_id
    with pytest.raises(SproutError): repo.set_preview_metadata(commit,first.id,file_ids=[other])
    with pytest.raises(sqlite3.IntegrityError),repo.connect() as db:
        db.execute('INSERT INTO preview_assets(attachment_id,commit_id,file_id) VALUES(?,?,?)',(first.id,commit,other))


def test_replace_delete_and_commit_recovery_keep_all_metadata_and_links(tmp_path):
    repo,commit,first,second,ids,source=setup(tmp_path)
    original=repo.set_preview_metadata(commit,first.id,display_name='review',description='notes',file_ids=ids)
    source.write_bytes(b'replacement')
    replaced=repo.replace_preview(commit,first.id,source)
    assert (replaced.display_name,replaced.description,replaced.file_ids)==('review','notes',tuple(sorted(ids)))
    assert (replaced.id,replaced.position,replaced.created_at)==(original.id,original.position,original.created_at)
    replace_record=repo.trash_items()[0]['id']
    repo.restore_trash(replace_record)
    assert repo.preview(commit,first.id)==original
    repo.delete_preview(commit,first.id)
    repo.restore_trash(repo.trash_items()[0]['id'])
    assert repo.preview(commit,first.id)==original
    repo.delete_commit(commit)
    repo.gc()
    repo.restore_trash(repo.trash_items()[0]['id'])
    assert repo.preview(commit,first.id)==original
    assert repo.doctor().ok


def test_metadata_edit_conflicts_with_older_preview_undo(tmp_path):
    repo,commit,first,second,ids,source=setup(tmp_path)
    source.write_bytes(b'new')
    repo.replace_preview(commit,first.id,source)
    item=repo.trash_items()[0]['id']
    repo.set_preview_metadata(commit,first.id,description='later edit',file_ids=ids)
    with pytest.raises(SproutError) as error: repo.restore_trash(item)
    assert error.value.code=='trash_restore_conflict'
    assert repo.preview(commit,first.id).description=='later edit'


def test_failed_link_update_rolls_back_metadata(tmp_path):
    repo,commit,first,second,ids,source=setup(tmp_path)
    with repo.connect() as db:
        db.execute("CREATE TRIGGER fail_link BEFORE INSERT ON preview_assets BEGIN SELECT RAISE(ABORT,'fail'); END")
    with pytest.raises(sqlite3.Error): repo.set_preview_metadata(commit,first.id,display_name='new',file_ids=ids)
    assert repo.preview(commit,first.id)==first


def test_material_links_follow_identity_across_rename_without_confusing_copies(tmp_path):
    repo,commit,first,second,ids,source=setup(tmp_path)
    original_id=repo.manifest(commit)['a.bin'].file_id
    other_id=repo.manifest(commit)['b.bin'].file_id
    repo.set_preview_metadata(commit,first.id,file_ids=[original_id])
    renamed=repo.root/'renamed.bin'
    repo.move(repo.root/'a.bin',renamed)
    later=repo.commit('renamed').commit_id
    new_preview=repo.add_previews(later,[source])[0]
    linked=repo.set_preview_metadata(later,new_preview.id,file_ids=[original_id])
    assert linked.file_ids==(original_id,)
    assert repo.manifest(later)['renamed.bin'].file_id==original_id
    assert other_id!=original_id
    assert repo.preview(commit,first.id).file_ids==(original_id,)


def test_invalid_material_recovery_context_is_rejected_without_changes(tmp_path):
    repo,commit,first,second,ids,source=setup(tmp_path)
    repo.set_preview_metadata(commit,first.id,file_ids=ids)
    repo.delete_preview(commit,first.id)
    item=repo.trash_items()[0]['id']
    with repo.connect() as db:
        payload=json.loads(db.execute('SELECT payload FROM trash_entries WHERE id=?',(item,)).fetchone()[0])
        payload['assets_after']=None
        db.execute('UPDATE trash_entries SET payload=? WHERE id=?',(json.dumps(payload),item))
    before=repo.previews(commit)
    with pytest.raises(SproutError) as error: repo.restore_trash(item)
    assert error.value.code=='invalid_trash_record'
    assert repo.previews(commit)==before


def test_retired_primary_storage_is_inert_across_replacement_and_recovery(tmp_path,monkeypatch):
    from sprout.serve import run_command

    repo,commit,first,second,ids,source=setup(tmp_path)
    original=repo.set_preview_metadata(commit,first.id,display_name='Review',description='Notes',file_ids=ids)
    with repo.connect() as db:
        # Simulate a V1 repository saved before the primary UI was retired.
        db.execute('UPDATE commit_attachments SET is_primary=1 WHERE id=?',(first.id,))
    reopened=Repository.discover(repo.root)
    assert reopened.preview(commit,first.id)==original
    assert not hasattr(original,'is_primary')
    monkeypatch.chdir(repo.root)
    for flag in ['--primary','--no-primary']:
        result=CliRunner().invoke(app,['preview','metadata',commit,first.id,flag])
        assert result.exit_code!=0
        assert repo.preview(commit,first.id)==original
    response=run_command(app,['preview','list',commit,'--json'])
    assert response['ok'] and 'is_primary' not in json.dumps(response['result'])
    repo.reorder_previews(commit,[second.id,first.id])
    original=repo.preview(commit,first.id)
    assert [item.id for item in Repository.discover(repo.root).previews(commit)]==[second.id,first.id]
    assert original.object_hash==first.object_hash
    source.write_bytes(b'replacement')
    repo.replace_preview(commit,first.id,source)
    record=repo.trash_items()[0]['id']
    assert 'is_primary' not in json.dumps(repo.trash_detail(record))
    assert 'is_primary' not in json.dumps(repo.restore_trash(record,dry_run=True))
    assert repo.restore_trash(record)['restored']
    assert repo.preview(commit,first.id)==original
    repo.delete_preview(commit,first.id)
    repo.restore_trash(repo.trash_items()[0]['id'])
    assert repo.preview(commit,first.id)==original
    assert not hasattr(repo.preview(commit,first.id),'is_primary')
    assert repo.doctor().ok
