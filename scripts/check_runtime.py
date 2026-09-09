"""Safe local checks: python -m scripts.check_runtime. No network model/provider calls."""
import argparse
import asyncio
import sys

from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.readiness import check_readiness
from app.database.session import get_engine


async def run_checks(settings_loader=get_settings, probe=check_readiness):
    try:
        settings = settings_loader()
        url = make_url(settings.database_url or "")
        valid = (url.drivername == "postgresql+psycopg" and bool(url.database)
                 and bool(settings.groq_api_key and settings.groq_api_key.strip())
                 and bool(settings.groq_model and settings.groq_model.strip())
                 and bool(settings.embedding_model and settings.reranker_model))
    except Exception:
        valid = False
    print("config: PASS" if valid else "config: FAIL (configuration_error)")
    if not valid:
        return 1
    result = await probe()
    for name, state in result.components().items():
        print(f"{name}: {'PASS' if state == 'ready' else 'FAIL (database_unavailable)'}")
    return 0 if result.ready else 1


async def _run():
    try:
        return await run_checks()
    finally:
        try:
            await get_engine().dispose()
        except Exception:
            pass


def main(argv=None):
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    try:
        kwargs = {"loop_factory": asyncio.SelectorEventLoop} if sys.platform == "win32" else {}
        return asyncio.run(_run(), **kwargs)
    except Exception:
        print("runtime: FAIL (internal_error)")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
