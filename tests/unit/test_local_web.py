import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app as api_app
from scripts.local_web import create_local_application


@pytest.mark.asyncio
async def test_local_page_assets_and_existing_api() -> None:
    app = create_local_application()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        page = await client.get("/m11/")
        assert page.status_code == 200
        assert 'id="asta-widget"' in page.text
        for path in ("css/asta-widget.css", "js/asta-widget.js", "js/asta-client.mjs"):
            response = await client.get(f"/m11/{path}")
            assert response.status_code == 200
            if path.endswith((".js", ".mjs")):
                assert response.headers["content-type"].split(";")[0] in {
                    "application/javascript", "text/javascript"
                }
        assert (await client.get("/api/v1/health")).status_code == 200
        schema = (await client.get("/openapi.json")).json()
        assert "/api/v1/chat/conversations/{conversation_id}/messages" in schema["paths"]
        assert "/m11/" not in schema["paths"]
        assert (await client.get("/m11")).headers["location"] == "/m11/"


@pytest.mark.asyncio
async def test_local_launcher_does_not_expose_repository_or_change_api_app() -> None:
    async with AsyncClient(transport=ASGITransport(app=create_local_application()), base_url="http://test") as client:
        for path in ("/.env", "/m11/.env", "/m11/tests/chat-client.test.mjs", "/m11/js/%2e%2e/%2e%2e/.env"):
            assert (await client.get(path)).status_code == 404
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        assert (await client.get("/m11/")).status_code == 404
