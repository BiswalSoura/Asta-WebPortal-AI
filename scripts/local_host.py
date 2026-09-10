"""Local M14 host simulation; no production static routes or deployment."""
from fastapi.responses import FileResponse
from scripts.local_web import FRONTEND, create_local_application


def create_host_application():
    app = create_local_application()

    @app.get("/m14/", include_in_schema=False)
    async def host_page():
        return FileResponse(FRONTEND / "host.html", headers={"Cache-Control": "no-store"})

    return app


if __name__ == "__main__":
    import asyncio
    import uvicorn
    asyncio.run(uvicorn.Server(uvicorn.Config(
        "scripts.local_host:create_host_application", factory=True,
        host="127.0.0.1", port=8014, access_log=False,
    )).serve(), loop_factory=asyncio.SelectorEventLoop)
