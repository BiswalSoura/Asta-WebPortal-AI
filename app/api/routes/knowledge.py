"""Internal administration: send raw file bytes, not multipart or browser role claims."""
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies.database import get_database_session
from app.api.dependencies.knowledge_admin import require_knowledge_admin
from app.api.dependencies.services import get_shared_embedding_service
from app.api.routes.operations_common import OperationsRoute, bounded_stream
from app.knowledge.constants import MAX_DOCUMENT_SIZE_BYTES
from app.services.knowledge_operations import KnowledgeOperations, safe_filename

router = APIRouter(prefix="/admin/knowledge", tags=["Internal knowledge administration"],
                   route_class=OperationsRoute, dependencies=[Depends(require_knowledge_admin)])


def get_knowledge_operations(session=Depends(get_database_session)):
    return KnowledgeOperations(session, embedding_service=get_shared_embedding_service())


@asynccontextmanager
async def write_operation(service):
    try:
        yield
        await service.session.commit()
        service.new_storage.clear()
    except BaseException:
        await service.session.rollback()
        service.cleanup()
        raise


async def upload(request, service, document_id=None):
    filename = safe_filename(request.headers.get('X-Filename', ''))
    # Authentication dependencies run before this body is consumed. Exact file limit,
    # enforced while streaming even with absent/misleading Content-Length.
    with TemporaryDirectory(prefix='asta-upload-') as temporary:
        path = Path(temporary) / filename
        with path.open('wb') as destination:
            async for part in bounded_stream(request, MAX_DOCUMENT_SIZE_BYTES):
                destination.write(part)
        async with write_operation(service):
            result = await service.ingest(path, document_id=document_id)
    return result


@router.post('', openapi_extra={"requestBody": {"required": True, "content": {
    "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}}, summary="Upload raw DOCX/PDF/TXT/MD bytes; X-Filename required")
async def upload_document(request: Request, service=Depends(get_knowledge_operations)):
    return await upload(request, service)


@router.put('/{document_id}', summary="New bytes, same original filename, existing version model")
async def update_document(document_id: UUID, request: Request,
                          service=Depends(get_knowledge_operations)):
    return await upload(request, service, document_id)


@router.get('')
async def list_documents(limit: int = Query(50, ge=1, le=100),
                         offset: int = Query(0, ge=0, le=100000),
                         service=Depends(get_knowledge_operations)):
    return {"documents": await service.documents(limit, offset), "limit": limit, "offset": offset}


@router.get('/{document_id}')
async def document_metadata(document_id: UUID, service=Depends(get_knowledge_operations)):
    return await service.document(document_id)


@router.get('/{document_id}/history')
async def document_history(document_id: UUID, limit: int = Query(50, ge=1, le=100),
                           offset: int = Query(0, ge=0, le=100000),
                           service=Depends(get_knowledge_operations)):
    return await service.history(document_id, limit, offset)


@router.post('/{document_id}/versions/{version_id}/reindex')
async def reindex_version(document_id: UUID, version_id: UUID, request: Request,
                          service=Depends(get_knowledge_operations)):
    async for _ in bounded_stream(request, 0):
        pass
    async with write_operation(service):
        result = await service.reindex(document_id, version_id)
    return result
