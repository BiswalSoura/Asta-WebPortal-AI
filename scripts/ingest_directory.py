"""Add approved files through ingestion AND indexing; no URLs, no implicit recursion."""
import argparse
import asyncio
from contextlib import redirect_stderr, redirect_stdout
import logging
import os
from pathlib import Path
import sys

from app.knowledge.constants import SUPPORTED_DOCUMENT_EXTENSIONS
from app.services.knowledge_operations import KnowledgeOperations, OperationsError, safe_filename

EXCLUDED = frozenset({'cache', 'reports', 'results', 'logs', 'uploads', 'node_modules',
                      'venv', 'env', '__pycache__', 'evaluation', 'outputs', 'work'})


def select_files(directory, recursive=False):
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink() or directory.is_junction():
        raise OperationsError('INVALID_DIRECTORY')
    selected = []
    # Prune before descent; never follow symlinks/junctions or hidden/generated folders.
    def unreadable(error):
        raise OperationsError('DIRECTORY_UNREADABLE') from None
    for current, dirs, files in os.walk(directory, followlinks=False, onerror=unreadable):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d.lower() not in EXCLUDED
            and not (Path(current)/d).is_symlink() and not (Path(current)/d).is_junction())
        for name in files:
            path = Path(current)/name
            if (not name.startswith('.') and path.suffix.lower() in SUPPORTED_DOCUMENT_EXTENSIONS
                    and not path.is_symlink() and not path.is_junction()):
                selected.append(path)
        if not recursive:
            break
    selected.sort(key=lambda p: (p.relative_to(directory).as_posix().casefold(),
                                p.relative_to(directory).as_posix()))
    # In the frozen ingestion model filename is identity. Ambiguous folder batches must fail.
    names = [p.name for p in selected]
    if len(names) != len(set(names)):
        raise OperationsError('DUPLICATE_FILENAMES')
    return selected


def display(path):
    try:
        return safe_filename(path.name)
    except OperationsError:
        return '[restricted filename]'


async def ingest_one(path):
    from app.api.dependencies.services import get_shared_embedding_service
    from app.database.session import get_session_factory
    async with get_session_factory()() as session:
        service = KnowledgeOperations(session, embedding_service=get_shared_embedding_service())
        try:
            result = await service.ingest(path)
            await session.commit()
            service.new_storage.clear()
            return result
        except BaseException:
            await session.rollback()
            service.cleanup()
            raise


async def process_files(files, *, dry_run=False, continue_on_error=False, processor=ingest_one):
    counts = {'indexed': 0, 'duplicate': 0, 'failed': 0, 'selected': len(files), 'unprocessed': 0}
    for index, path in enumerate(files):
        if dry_run:
            print(f'{display(path)}: selected')
            continue
        try:
            # Third-party loader/model output is not part of this public CLI contract.
            with open(os.devnull, 'w') as sink, redirect_stdout(sink), redirect_stderr(sink):
                result = await processor(path)
            kind = 'duplicate' if result['duplicate'] else 'indexed'
            counts[kind] += 1
            print(f'{display(path)}: {kind}; embeddings={result["indexed_chunks"]}; '
                  f'version={result["version_number"]}; active={result["active"]}')
        except Exception as exc:
            counts['failed'] += 1
            code = exc.code if isinstance(exc, OperationsError) else 'PROCESSING_FAILED'
            print(f'{display(path)}: failed ({code})')
            if not continue_on_error:
                counts['unprocessed'] = len(files)-index-1
                break
    print('Summary: ' + ', '.join(f'{key}={value}' for key, value in counts.items()))
    return 1 if counts['failed'] else 0


async def run(arguments):
    try:
        files = [arguments.file] if arguments.file else select_files(arguments.directory, arguments.recursive)
        if arguments.file and (not arguments.file.is_file() or arguments.file.is_symlink()):
            raise OperationsError('INVALID_FILE')
        if arguments.file:
            safe_filename(arguments.file.name)
        return await process_files(files, dry_run=arguments.dry_run,
                                   continue_on_error=arguments.continue_on_error)
    finally:
        if not arguments.dry_run:
            from app.database.session import get_engine
            await get_engine().dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, nargs='?')
    parser.add_argument('--file', type=Path, help='Explicit single-file ingestion and indexing')
    parser.add_argument('--recursive', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--continue-on-error', action='store_true', help='Commit successes; return 1 if any file fails')
    args = parser.parse_args(argv)
    if bool(args.directory) == bool(args.file) or (args.file and args.recursive):
        parser.error('Supply either a directory or --file; --recursive applies to a directory')
    old_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        kwargs = {'loop_factory': asyncio.SelectorEventLoop} if sys.platform == 'win32' else {}
        return asyncio.run(run(args), **kwargs)
    except Exception as exc:
        code = exc.code if isinstance(exc, OperationsError) else 'PROCESSING_FAILED'
        print(f'FAIL: {code}')
        return 1
    finally:
        logging.disable(old_logging)


if __name__ == '__main__':
    raise SystemExit(main())
