from pathlib import Path
import pytest
from scripts.ingest_directory import select_files, process_files
from app.services.knowledge_operations import OperationsError
from scripts.check_repository_safety import unsafe_content


def test_selection_dry_run_order_exclusions(tmp_path, capsys):
    for name in ['z.md', 'a.docx', 'B.pdf', 'ignore.exe', '.env', '.hidden.md']:
        (tmp_path/name).touch()
    for folder in ['reports', '.cache', 'nested', 'node_modules']:
        (tmp_path/folder).mkdir()
        (tmp_path/folder/'child.txt').touch()
    assert [p.name for p in select_files(tmp_path)] == ['a.docx', 'B.pdf', 'z.md']
    assert [p.name for p in select_files(tmp_path, True)] == ['a.docx', 'B.pdf', 'child.txt', 'z.md']


@pytest.mark.asyncio
async def test_dry_run_never_processes(tmp_path, capsys):
    async def forbidden(path):
        raise AssertionError('called')
    assert await process_files([tmp_path/'approved.md'], dry_run=True, processor=forbidden) == 0
    assert 'selected=1' in capsys.readouterr().out


@pytest.mark.asyncio
@pytest.mark.parametrize('continue_on_error, expected', [(False, 2), (True, 3)])
async def test_partial_failure_and_duplicates(continue_on_error, expected, capsys):
    calls = []
    async def process(path):
        calls.append(path.name)
        if path.name == 'b.md':
            raise ValueError('secret-raw-error')
        return {'duplicate': True, 'indexed_chunks': 0, 'version_number': 1, 'active': True}
    assert await process_files([Path(n) for n in ['a.md','b.md','c.md']],
        continue_on_error=continue_on_error, processor=process) == 1
    assert len(calls) == expected
    out = capsys.readouterr().out
    assert 'failed=1' in out and 'secret-raw-error' not in out
    assert 'duplicate' in out


def test_colliding_filenames_refused(tmp_path):
    (tmp_path/'a').mkdir()
    (tmp_path/'same.md').touch()
    (tmp_path/'a'/'same.md').touch()
    with pytest.raises(OperationsError, match='DUPLICATE_FILENAMES'):
        select_files(tmp_path, True)


def test_repository_admin_token_signatures():
    key = 'KNOWLEDGE_' + 'ADMIN_TOKEN'
    assert unsafe_content(key + '=' + 'abc123'*8)
    assert unsafe_content('"'+key+'": "'+'abc123'*8+'"')
    assert not unsafe_content(key + '=\n')
