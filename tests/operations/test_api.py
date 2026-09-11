from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.application import create_application
from app.core.config import Settings, get_settings
from app.api.routes.knowledge import get_knowledge_operations
from app.api.dependencies.database import get_database_session
from app.api.routes import feedback
from app.knowledge.constants import MAX_DOCUMENT_SIZE_BYTES
from app.services.knowledge_operations import safe_filename, OperationsError


class Session:
    async def commit(self):
        pass
    async def rollback(self):
        pass


class FakeOperations:
    def __init__(self):
        self.session = Session()
        self.new_storage = []
        self.calls = []
    def cleanup(self):
        pass
    async def ingest(self, path, document_id=None):
        self.calls.append((path.name, path.read_bytes()))
        return {'duplicate': False, 'indexed_chunks': 1}


@pytest.fixture
def client():
    app = create_application()
    settings = Settings(_env_file=None)
    service = FakeOperations()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_knowledge_operations] = lambda: service
    async def session():
        yield Session()
    app.dependency_overrides[get_database_session] = session
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, settings, service


def enable(settings):
    settings.knowledge_admin_api_enabled = True
    token = 'local-test-' + 'x' * 40
    settings.knowledge_admin_token = SecretStr(token)
    return {'X-Asta-Admin-Token': token, 'X-Filename': 'approved.md'}


def test_default_disabled_and_public_health(client):
    c, settings, service = client
    assert Settings(_env_file=None).knowledge_admin_api_enabled is False
    assert c.post('/api/v1/admin/knowledge', content=b'secret').status_code == 404
    assert not service.calls
    assert c.get('/api/v1/health').status_code == 200


@pytest.mark.parametrize('supplied', ['', 'wrong', '\u00e9', 'x' * 513])
def test_bad_token(client, supplied):
    c, settings, service = client
    headers = enable(settings)
    # Raw UTF-8 tests constant-time bytes comparison without an ASCII-only exception.
    headers['X-Asta-Admin-Token'] = supplied.encode()
    response = c.post('/api/v1/admin/knowledge', headers=headers, content=b'private-body')
    assert response.status_code == 401
    assert not service.calls
    assert 'private-body' not in response.text


def test_missing_config_fails_closed(client):
    c, settings, _ = client
    settings.knowledge_admin_api_enabled = True
    assert c.get('/api/v1/admin/knowledge').status_code == 503


@pytest.mark.parametrize('extension', ['md', 'txt', 'docx', 'pdf'])
def test_authorized_upload_bounded_and_private(client, extension, capsys):
    c, settings, service = client
    headers = enable(settings)
    headers['X-Filename'] = 'approved.' + extension
    response = c.post('/api/v1/admin/knowledge', headers=headers, content=b'private-upload-sentinel')
    assert response.status_code == 200
    assert service.calls == [('approved.' + extension, b'private-upload-sentinel')]
    combined = response.text + capsys.readouterr().out
    assert 'private-upload-sentinel' not in combined
    assert headers['X-Asta-Admin-Token'] not in combined
    assert response.headers['X-Request-ID']


@pytest.mark.parametrize('name', ['../x.md', '..\\x.md', 'C:\\x.md', '/tmp/x.md',
    'a:evil.md', 'NUL.txt', '.env', 'a\n.md', 'x.md ', 'x'*181+'.md'])
def test_filename_rejected(name):
    with pytest.raises(OperationsError):
        safe_filename(name)


def test_unsupported_rejected_before_processing(client):
    c, settings, service = client
    headers = enable(settings)
    headers['X-Filename'] = 'run.exe'
    assert c.post('/api/v1/admin/knowledge', headers=headers, content=b'abc').status_code == 415
    assert not service.calls


def test_oversize_header_rejected(client):
    c, settings, service = client
    headers = enable(settings)
    headers['Content-Length'] = str(MAX_DOCUMENT_SIZE_BYTES + 1)
    assert c.post('/api/v1/admin/knowledge', headers=headers, content=b'abc').status_code == 413
    assert not service.calls


def test_oversize_stream_rejected(client):
    c, settings, service = client
    headers = enable(settings)
    # No Content-Length: enforcement must count received bytes.
    content = (b'x' * (1024*1024) for _ in range(21))
    assert c.post('/api/v1/admin/knowledge', headers=headers, content=content).status_code == 413
    assert not service.calls


def test_loader_exception_sanitized(client, capsys):
    c, settings, service = client
    async def broken(*args, **kwargs):
        raise ValueError('private-body C:/private/path token-sentinel')
    service.ingest = broken
    r = c.post('/api/v1/admin/knowledge', headers=enable(settings), content=b'body')
    assert r.status_code == 500
    output = r.text + capsys.readouterr().out
    assert 'token-sentinel' not in output and 'C:/private/path' not in output


@pytest.mark.parametrize('payload', [
    {'is_positive': 'true'}, {'is_positive': 1}, {'is_positive': False, 'category': 'bad'},
    {'is_positive': True, 'comment': 'private-sentinel'}, {'rating': -1},
])
def test_feedback_invalid_contract(client, payload):
    c, _, _ = client
    r = c.post('/api/v1/feedback', json={'conversation_id': str(uuid4()),
        'message_id': str(uuid4()), **payload})
    assert r.status_code == 422
    assert 'private-sentinel' not in r.text


def test_feedback_size_limit(client):
    c, _, _ = client
    r = c.post('/api/v1/feedback', content=b'x'*1025, headers={'Content-Type':'application/json'})
    assert r.status_code == 413


def test_feedback_valid_api(client, monkeypatch):
    c, _, _ = client
    async def record(session, **payload):
        assert payload['is_positive'] is False
        assert set(payload) == {'conversation_id', 'message_id', 'is_positive'}
        return {'status': 'recorded'}
    monkeypatch.setattr(feedback, 'record_feedback', record)
    r = c.post('/api/v1/feedback', json={'conversation_id': str(uuid4()),
        'message_id': str(uuid4()), 'is_positive': False})
    assert r.json() == {'status': 'recorded'}
