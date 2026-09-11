"""Read-only safe counts/metadata for local operators. Does not print content or paths."""
import argparse
import asyncio
import json
import sys
from uuid import UUID
from app.database.session import get_engine, get_session_factory
from app.services.knowledge_operations import KnowledgeOperations


async def run(args):
    try:
        async with get_session_factory()() as session:
            service = KnowledgeOperations(session)
            result = await service.history(args.document_id) if args.document_id else await service.documents(args.limit)
            print(json.dumps(result, default=str, indent=2))
    finally:
        await get_engine().dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document-id', type=UUID)
    parser.add_argument('--limit', type=int, default=50, choices=range(1, 101))
    args = parser.parse_args(argv)
    try:
        kwargs = {'loop_factory': asyncio.SelectorEventLoop} if sys.platform == 'win32' else {}
        asyncio.run(run(args), **kwargs)
        return 0
    except Exception:
        print('FAIL: KNOWLEDGE_STATUS_UNAVAILABLE')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
