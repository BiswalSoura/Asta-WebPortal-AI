"""M11 standalone local page; the production app factory is unchanged."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.application import create_application


FRONTEND = Path(__file__).resolve().parents[1] / "frontend"


def create_local_application() -> FastAPI:
    application = create_application()

    @application.get("/m11", include_in_schema=False)
    async def redirect_to_page() -> RedirectResponse:
        return RedirectResponse("/m11/")

    @application.get("/m11/", include_in_schema=False)
    async def local_page() -> FileResponse:
        return FileResponse(FRONTEND / "index.html", headers={"Cache-Control": "no-store"})

    @application.get("/m11/js/asta-client.mjs", include_in_schema=False)
    async def client_module() -> FileResponse:
        # Windows MIME registry entries can label .mjs as text/plain.
        return FileResponse(FRONTEND / "js" / "asta-client.mjs", media_type="application/javascript")

    # Expose only the two public asset folders, never the repository or its .env.
    application.mount("/m11/css", StaticFiles(directory=FRONTEND / "css"), name="m11-css")
    application.mount("/m11/js", StaticFiles(directory=FRONTEND / "js"), name="m11-js")
    return application


if __name__ == "__main__":
    import uvicorn

    # Match the existing CLI's selector loop, required by async Psycopg on Windows.
    uvicorn.run(
        "scripts.local_web:create_local_application",
        factory=True,
        host="127.0.0.1",
        port=8000,
        loop="asyncio:SelectorEventLoop",
    )
