from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from app.core.config import Settings, get_settings
from app.application import create_application
from app.api.dependencies import get_conversation_service, get_database_session
from scripts.local_host import create_host_application

@pytest.mark.parametrize('origin', ['*', 'https://*.example.test', 'https://example.test/', 'https://u:p@example.test', 'https://example.test?x=1', 'null', 'https://example.test:bad', 'https://example.test\\evil'])
def test_invalid_origins(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_allowed_origins=[origin])

@pytest.mark.asyncio
@pytest.mark.parametrize('expose', [False, True])
async def test_exact_cors_and_header_exposure(monkeypatch, expose):
    monkeypatch.setenv('ASTA_CORS_ALLOWED_ORIGINS', '["https://host.example.test"]')
    monkeypatch.setenv('ASTA_CORS_EXPOSE_REQUEST_ID', str(expose))
    get_settings.cache_clear()
    try:
        async with AsyncClient(transport=ASGITransport(app=create_application()), base_url='http://test') as client:
            for origin, allowed in [('https://host.example.test', True), ('https://evil.test', False), ('https://host.example.test.evil.test', False)]:
                response = await client.get('/api/v1/health', headers={'Origin': origin})
                assert bool(response.headers.get('access-control-allow-origin')) == allowed
                assert response.headers.get('x-request-id')
                if allowed:
                    assert response.headers['access-control-allow-origin'] == origin
                assert ('X-Request-ID' in response.headers.get('access-control-expose-headers', '')) == expose
                preflight = await client.options('/api/v1/chat/conversations', headers={'Origin': origin, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type'})
                assert preflight.status_code == (200 if allowed else 400)
    finally:
        get_settings.cache_clear()

@pytest.mark.asyncio
async def test_optional_context_is_metadata_and_identity_is_rejected():
    app = create_application()
    calls = []
    class Service:
        async def start_conversation(self, **kwargs):
            calls.append(kwargs)
            return uuid4()
    class Session:
        async def commit(self): pass
    async def session(): yield Session()
    app.dependency_overrides[get_database_session] = session
    app.dependency_overrides[get_conversation_service] = Service
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        assert (await client.post('/api/v1/chat/conversations')).status_code == 201
        assert calls[-1] == {}
        response = await client.post('/api/v1/chat/conversations', json={'page_context': 'fixture-a'})
        assert response.status_code == 201
        assert calls[-1] == {'page_context': {'host_page_context': 'fixture-a'}}
        assert set(response.json()) == {'conversation_id', 'status'}
        for body in [{'page_context': '<img>'}, {'page_context': 'x'*129}, {'page_context': {'role': 'admin'}}, {'user_role': 'admin'}, {'permission_context': {}}, {'user_id': 'x'}]:
            assert (await client.post('/api/v1/chat/conversations', json=body)).status_code == 422
        assert len(calls) == 2

@pytest.mark.asyncio
async def test_fixture_modules_mime_and_private_files():
    async with AsyncClient(transport=ASGITransport(app=create_host_application()), base_url='http://test') as client:
        assert (await client.get('/m14/')).status_code == 200
        for module in ['asta-widget-core', 'asta-embed', 'host-demo']:
            response = await client.get(f'/m11/js/{module}.mjs')
            assert response.status_code == 200
            assert response.headers['content-type'].startswith('application/javascript')
        for path in ['/m14/.env', '/m11/js/private.mjs', '/m14/tests/embed.test.mjs']:
            assert (await client.get(path)).status_code == 404
