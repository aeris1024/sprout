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
    changed=repo.set_preview_metadata(commit,first.id,display_name='  Cafe\u0301  ',description='first\nsecond')
    assert changed.display_name=='Café' and changed.description=='first\nsecond'
    assert not hasattr(changed,'file_ids')
    assert changed.original_name==first.original_name and changed.object_hash==first.object_hash
    monkeypatch.chdir(repo.root)
    output=CliRunner().invoke(app,['leaf','preview','edit',commit,first.id,'--name=Review','--description=Notes','--json'])
    assert output.exit_code==0,output.exception
    assert 'file_ids' not in json.loads(output.stdout)
    assert 'is_primary' not in json.loads(output.stdout)
    archive=tmp_path/'archive'; repo.archive(archive)
    record=json.loads((archive/'archive.json').read_text(encoding='utf-8'))['commits'][0]
    assert record['previews'][0]['display_name']=='Review'
    assert 'is_primary' not in record['previews'][0]
    assert 'Review' in (archive/record['directory']/'index.html').read_text(encoding='utf-8')
    assert Repository.discover(repo.root).preview(commit,first.id).display_name=='Review'
    empty=repo.set_preview_metadata(commit,first.id,display_name='',description='')
    assert not empty.display_name and not empty.description


@pytest.mark.parametrize('options',[{'display_name':'x'*257},{'display_name':'bad\nname'},{'description':'x'*20001}])
def test_invalid_metadata_update_is_atomic(tmp_path,options):
    repo,commit,first,second,ids,source=setup(tmp_path)
    before=repo.previews(commit)
    with pytest.raises(SproutError):
        repo.set_preview_metadata(commit,first.id,**options)
    assert repo.previews(commit)==before


def test_retired_links_have_no_public_metadata_api(tmp_path):
    repo,commit,first,second,ids,source=setup(tmp_path)
    with pytest.raises(TypeError):
        repo.set_preview_metadata(commit,first.id,file_ids=ids)
    assert repo.preview(commit,first.id)==first


def test_replace_delete_and_commit_recovery_keep_all_metadata(tmp_path):
    repo,commit,first,second,ids,source=setup(tmp_path)
    original=repo.set_preview_metadata(commit,first.id,display_name='review',description='notes')
    source.write_bytes(b'replacement')
    replaced=repo.replace_preview(commit,first.id,source)
    assert (replaced.display_name,replaced.description)==('review','notes')
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
    repo.set_preview_metadata(commit,first.id,description='later edit')
    with pytest.raises(SproutError) as error: repo.restore_trash(item)
    assert error.value.code=='trash_restore_conflict'
    assert repo.preview(commit,first.id).description=='later edit'


def test_failed_metadata_update_rolls_back_all_fields(tmp_path):
    repo,commit,first,second,ids,source=setup(tmp_path)
    with repo.connect() as db:
        db.execute("CREATE TRIGGER fail_metadata BEFORE UPDATE ON commit_attachments BEGIN SELECT RAISE(ABORT,'fail'); END")
    with pytest.raises(sqlite3.Error): repo.set_preview_metadata(commit,first.id,display_name='new',description='changed')
    assert repo.preview(commit,first.id)==first


def test_leaf_wide_previews_do_not_change_file_identity_or_cover(tmp_path):
    repo,commit,first,second,ids,source=setup(tmp_path)
    original_id=repo.manifest(commit)['a.bin'].file_id
    other_id=repo.manifest(commit)['b.bin'].file_id
    repo.set_cover(repo.root/'a.bin')
    cover=repo.cover_file()
    repo.set_preview_metadata(commit,first.id,display_name='Whole leaf')
    renamed=repo.root/'renamed.bin'
    repo.move(repo.root/'a.bin',renamed)
    later=repo.commit('renamed').commit_id
    new_preview=repo.add_previews(later,[source])[0]
    edited=repo.set_preview_metadata(later,new_preview.id,description='Whole leaf notes')
    assert not hasattr(edited,'file_ids')
    assert repo.manifest(later)['renamed.bin'].file_id==original_id
    assert other_id!=original_id
    assert repo.cover_file()[0]==cover[0]
    assert repo.preview(commit,first.id).display_name=='Whole leaf'


def test_invalid_material_recovery_context_is_rejected_without_changes(tmp_path):
    repo,commit,first,second,ids,source=setup(tmp_path)
    with repo.connect() as db:
        db.execute('INSERT INTO preview_assets(attachment_id,commit_id,file_id) VALUES(?,?,?)',(first.id,commit,ids[0]))
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
    original=repo.set_preview_metadata(commit,first.id,display_name='Review',description='Notes')
    with repo.connect() as db:
        # Simulate a V1 repository saved before the primary UI was retired.
        db.execute('UPDATE commit_attachments SET is_primary=1 WHERE id=?',(first.id,))
    reopened=Repository.discover(repo.root)
    assert reopened.preview(commit,first.id)==original
    assert not hasattr(original,'is_primary')
    monkeypatch.chdir(repo.root)
    for flag in ['--primary','--no-primary']:
        result=CliRunner().invoke(app,['leaf', 'preview', 'edit', commit, first.id, flag])
        assert result.exit_code!=0
        assert repo.preview(commit,first.id)==original
    response=run_command(app,['leaf', 'preview', 'list', commit, '--json'])
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


@pytest.mark.parametrize('operation',['replace','delete','commit'])
def test_stored_material_links_stay_inert_through_recovery_and_archive(tmp_path,operation):
    repo,commit,first,second,ids,source=setup(tmp_path)
    original=repo.set_preview_metadata(commit,first.id,display_name='Review',description='Notes')
    with repo.connect() as db:
        db.execute('INSERT INTO preview_assets(attachment_id,commit_id,file_id) VALUES(?,?,?)',(first.id,commit,ids[0]))
    assert Repository.discover(repo.root).preview(commit,first.id)==original
    assert not hasattr(original,'file_ids')
    if operation=='replace':
        source.write_bytes(b'updated')
        repo.replace_preview(commit,first.id,source)
    elif operation=='delete':
        repo.delete_preview(commit,first.id)
    else:
        repo.delete_commit(commit)
    record=repo.trash_items()[0]['id']
    shown=json.dumps(repo.trash_detail(record))
    assert 'preview_assets' not in shown and 'file_ids' not in shown
    assert repo.restore_trash(record,dry_run=True)['dry_run']
    assert repo.restore_trash(record)['restored']
    assert repo.preview(commit,first.id)==original
    assert [item.id for item in repo.previews(commit)]==[first.id,second.id]
    archive=tmp_path/'archive'; repo.archive(archive)
    model=json.loads((archive/'archive.json').read_text(encoding='utf-8'))
    assert 'file_ids' not in json.dumps(model)
    html=(archive/model['commits'][0]['directory']/'index.html').read_text(encoding='utf-8')
    assert '対象素材' not in html and 'Review' in html
    assert repo.doctor().ok


def test_canonical_leaf_preview_commands_and_removed_link_options(tmp_path,monkeypatch):
    from PIL import Image
    from sprout.serve import run_command

    repo,commit,first,second,ids,source=setup(tmp_path)
    monkeypatch.chdir(repo.root)
    runner=CliRunner()

    def call(*args):
        result=runner.invoke(app,['leaf','preview',*args,'--json'])
        assert result.exit_code==0,result.output
        return json.loads(result.stdout)

    image=tmp_path/'review.png'; Image.new('RGB',(20,10),'blue').save(image)
    attached=call('add',commit,str(image))[0]
    edited=call('edit',commit,attached['id'],'--name=  Cafe\u0301  ','--description=first\nsecond')
    assert edited['display_name']=='Café' and edited['description']=='first\nsecond'
    for option in ['--file-id','--clear-materials']:
        before=repo.preview(commit,attached['id'])
        args=['leaf','preview','edit',commit,attached['id'],option]
        if option=='--file-id': args.append(ids[0])
        result=runner.invoke(app,args)
        assert result.exit_code!=0 and repo.preview(commit,attached['id'])==before
    displayed=call('image',commit,attached['id'])
    assert displayed['width']==20 and displayed['height']==10
    call('order',commit,attached['id'],second.id,first.id)
    assert [item['id'] for item in call('list',commit)]==[attached['id'],second.id,first.id]
    response=run_command(app,['leaf','preview','list',commit,'--json'])
    assert response['ok'] and response['result']==call('list',commit)
    replaced=call('replace',commit,attached['id'],str(source))
    assert (replaced['id'],replaced['position'],replaced['created_at'],replaced['display_name'],replaced['description'])==(attached['id'],0,attached['created_at'],'Café','first\nsecond')
    output=tmp_path/'exported.wav'
    call('export',commit,attached['id'],'--output',str(output))
    assert output.read_bytes()==source.read_bytes()
    assert call('delete',commit,attached['id'])['deleted']
    restored=repo.restore_trash(repo.trash_items()[0]['id'])
    assert restored['restored'] and repo.preview(commit,attached['id']).display_name=='Café'
    assert not {'file_ids','is_primary'} & call('list',commit)[0].keys()
    help_result=runner.invoke(app,['leaf','preview','--help'])
    assert help_result.exit_code==0 and 'metadata' not in help_result.stdout
