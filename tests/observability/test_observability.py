import asyncio
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import structlog
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError

from app.application import create_application
from app.api.dependencies import get_conversation_service, get_database_session
from app.api.routes.ready import readiness_probe
from app.core.exceptions import AstaError, ConfigurationError
from app.core.readiness import Readiness, check_readiness
from app.core.telemetry import ERROR_CODES, classify_error, emit
from app.conversation import ConversationNotFoundError
from app.llm.exceptions import LLMRequestError
from app.llm.models import LLMResponse
from app.rag.rag_service import RAGService
from app.retrieval.models import RetrievalCandidate
from app.services.asta_service import AstaService
from app.services.conversation_service import ConversationService
from scripts.check_runtime import run_checks, main

SECRET = 'secret-credential-marker'
QUESTION = 'How do I create a project? private-message-marker'
ANSWER = 'Use Create New Project. private-answer-marker'


def records(capsys):
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()
            if line.startswith('{')]


@pytest.mark.parametrize('incoming', [None, '', 'unsafe value', 'x'*65, '../secret', 'bad\nvalue'])
def test_replaced_request_ids(incoming):
    app = create_application()
    with TestClient(app) as client:
        response = client.get('/api/v1/health', headers={} if incoming is None else {'X-Request-ID': incoming})
    assert response.status_code == 200
    UUID(response.headers['x-request-id'])
    assert response.headers['x-request-id'] != incoming


@pytest.mark.parametrize('incoming', ['asta-test-request-123', 'A.b_c-9', 'a'*64])
def test_preserved_id(incoming):
    response = TestClient(create_application()).get('/api/v1/health', headers={'X-Request-ID': incoming})
    assert response.headers['x-request-id'] == incoming


def test_safe_http_events_and_errors(capsys):
    app = create_application()
    @app.get('/fail')
    async def fail():
        raise RuntimeError(SECRET)
    @app.get('/handled')
    async def handled():
        raise AstaError(SECRET)
    client = TestClient(app, raise_server_exceptions=False)
    for path, status in [('/api/v1/health',200),('/fail',500),('/handled',400),('/unknown/'+SECRET,404)]:
        r = client.get(path+'?token='+SECRET, headers={'X-Request-ID':'safe-id',
                       'Authorization':'Bearer '+SECRET, 'Cookie':SECRET})
        assert r.status_code == status
        assert r.headers['x-request-id'] == 'safe-id'
        if status == 500:
            assert r.json() == {'error':{'code':'INTERNAL_SERVER_ERROR',
                'message':'An unexpected error occurred.'}, 'request_id':'safe-id'}
    events = records(capsys)
    assert SECRET not in json.dumps(events)
    completions = [e for e in events if e['event']=='request_completed']
    assert len(completions)==4
    for e in completions:
        assert e['request_id']=='safe-id'
        assert e['method']=='GET'
        assert type(e['elapsed_ms']) in (float,int) and e['elapsed_ms']>=0
        assert e['service']=='Asta' and e['version']=='0.1.0'
        assert e['route'] in {'unmatched','/api/v1/health'}
        assert e['error_code'] in ERROR_CODES
    assert 'exception' not in json.dumps(events)


def test_allowlist_ignores_payload_and_ambient_context(capsys):
    create_application()
    structlog.contextvars.bind_contextvars(prompt=SECRET, authorization=SECRET)
    try:
        emit('chat_outcome', path='rag', outcome='grounded', grounded=True,
             question=QUESTION, answer=ANSWER, prompt=SECRET, Authorization=SECRET,
             Cookie=SECRET, database_url='postgresql://u:password@host/db',
             settings={'key':SECRET}, error_code=SECRET, model=SECRET)
        assert structlog.contextvars.get_contextvars()['prompt']==SECRET
    finally:
        structlog.contextvars.clear_contextvars()
    events = records(capsys)
    content = json.dumps(events)
    for forbidden in [SECRET, QUESTION, ANSWER, 'postgresql', 'Authorization', 'Cookie', 'settings']:
        assert forbidden not in content
    assert events[-1]['outcome']=='grounded'


@pytest.mark.parametrize('result,status', [(Readiness(True,True),200),(Readiness(),503),(Readiness(True,False),503)])
def test_readiness_contract(result,status,monkeypatch):
    app = create_application()
    app.dependency_overrides[readiness_probe] = lambda: result
    def forbidden(*args, **kwargs):
        raise AssertionError('Model/provider boundary invoked')
    import app.api.dependencies.services as dependencies
    for name in ['get_shared_embedding_service','get_shared_reranker','get_shared_llm_client']:
        monkeypatch.setattr(dependencies,name,forbidden)
    response = TestClient(app).get('/api/v1/ready')
    assert response.status_code == status
    assert response.json()=={'status':'ready' if status==200 else 'not_ready',
        'service':'Asta','version':'0.1.0','components':result.components()}
    assert response.headers['x-request-id']
    assert TestClient(app).get('/api/v1/health').json()=={
        'status':'healthy','service':'Asta','version':'0.1.0','environment':'development'}


class Connection:
    def __init__(self, fail=False, vector=True):
        self.fail, self.vector = fail, vector
        self.queries=[]
    async def __aenter__(self):
        if self.fail:
            raise RuntimeError(SECRET)
        return self
    async def __aexit__(self,*args):
        pass
    async def execute(self,query):
        self.queries.append(str(query))
    async def scalar(self,query):
        self.queries.append(str(query))
        return self.vector
    def connect(self):
        return self


@pytest.mark.asyncio
@pytest.mark.parametrize('fail,vector', [(False,True),(True,False),(False,False)])
async def test_probe_actual_queries(fail,vector,capsys):
    engine=Connection(fail,vector)
    result=await check_readiness(engine)
    assert result.ready == (not fail and vector)
    if not fail:
        assert engine.queries==['SELECT 1', "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"]
    assert SECRET not in capsys.readouterr().out


@pytest.mark.parametrize('exc,code', [
    (ConfigurationError(SECRET),'configuration_error'),
    (OperationalError('SQL '+SECRET,{},Exception(SECRET)),'database_unavailable'),
    (ConversationNotFoundError(uuid4()),'conversation_not_found'),
    (LLMRequestError(SECRET),'provider_unavailable'),
    (RuntimeError(SECRET),'internal_error'),(AstaError(SECRET),'application_error')])
def test_classification(exc,code):
    assert classify_error(exc)==code
    assert classify_error(status_code=422)=='validation_error'


class Retrieval:
    def __init__(self, evidence):
        self.evidence=evidence
    async def search(self,query):
        if not self.evidence:
            return []
        return [RetrievalCandidate(chunk_id=uuid4(),document_id=uuid4(),document_name=SECRET,
            original_filename=SECRET,content='Create New Project '+SECRET,section_title=SECRET,
            page_number=None,source_metadata={},vector_score=.9,rerank_score=.95)]


class LLM:
    called=False
    async def generate(self,**kwargs):
        self.called=True
        return LLMResponse(content=ANSWER,model=SECRET,prompt_tokens=1,completion_tokens=1,total_tokens=2)


@pytest.mark.asyncio
@pytest.mark.parametrize('question,evidence,path,outcome,called', [
    ('Tell me a joke.',True,'guardrail_bypass','bypass',False),
    (QUESTION,False,'rag','insufficient_information',False),
    (QUESTION,True,'rag','grounded',True)])
async def test_pipeline_events(question,evidence,path,outcome,called,capsys):
    create_application()
    llm=LLM()
    service=AstaService(rag_service=RAGService(retrieval_service=Retrieval(evidence),llm_client=llm))
    await service.ask(question)
    events=records(capsys)
    event=next(e for e in events if e['event']=='chat_outcome')
    assert event['path']==path and event['outcome']==outcome
    assert event['model_used']==called and llm.called==called
    assert event['source_count']==int(called)
    assert bool([e for e in events if e.get('stage')=='llm'])==called
    for forbidden in [SECRET,QUESTION,ANSWER,question]:
        assert forbidden not in json.dumps(events)


@pytest.mark.asyncio
async def test_concurrent_context_isolation(capsys):
    app=create_application()
    @app.get('/concurrent')
    async def concurrent():
        await asyncio.sleep(.01)
        emit('stage_started', stage='rag')
        return {}
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        replies=await asyncio.gather(*[client.get('/concurrent',headers={'X-Request-ID':f'id-{i}'}) for i in range(8)])
    assert [r.headers['x-request-id'] for r in replies]==[f'id-{i}' for i in range(8)]
    events=records(capsys)
    assert {e['request_id'] for e in events if e['event']=='stage_started'}=={f'id-{i}' for i in range(8)}
    assert 'request_id' not in structlog.contextvars.get_contextvars()


@pytest.mark.asyncio
@pytest.mark.parametrize('configured,ready,expected', [(True,True,0),(True,False,1),(False,True,1)])
async def test_cli_checks(configured,ready,expected,capsys):
    settings=SimpleNamespace(database_url='postgresql+psycopg://u:password@host/db' if configured else SECRET,
        groq_api_key=SECRET,groq_model='model',embedding_model='embedding',reranker_model='reranker')
    async def probe():
        return Readiness(ready,ready)
    assert await run_checks(lambda:settings,probe)==expected
    output=capsys.readouterr().out
    assert SECRET not in output and 'password' not in output and 'host' not in output


def test_cli_main_exit_codes(monkeypatch,capsys):
    import scripts.check_runtime as cli
    async def fail():
        raise RuntimeError(SECRET)
    monkeypatch.setattr(cli,'_run',fail)
    assert main([])==1
    assert capsys.readouterr().out=='runtime: FAIL (internal_error)\n'
    async def success():
        return 0
    monkeypatch.setattr(cli,'_run',success)
    assert main([])==0


@pytest.mark.asyncio
async def test_api_propagates_id_to_existing_message_storage(capsys):
    app=create_application()
    stored=[]
    class Repository:
        async def get_conversation(self, id):
            return SimpleNamespace(id=id)
        async def get_recent_messages(self, **kwargs):
            return []
        async def add_message(self, **kwargs):
            stored.append(kwargs)
    service=ConversationService(None,repository=Repository(),
        responder=AstaService(rag_service=RAGService(retrieval_service=Retrieval(True),llm_client=LLM())))
    class Session:
        async def commit(self): pass
        async def rollback(self): pass
    async def session(): yield Session()
    app.dependency_overrides[get_database_session]=session
    app.dependency_overrides[get_conversation_service]=lambda:service
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post(f'/api/v1/chat/conversations/{uuid4()}/messages',
            json={'message':QUESTION},headers={'X-Request-ID':'storage-id','Authorization':SECRET,'Cookie':SECRET})
        invalid=await client.post('/api/v1/chat/conversations/bad-id/messages',json={'message':''})
    assert response.status_code==200
    assert set(response.json())=={'conversation_id','answer','sources'}
    assert len(stored)==2 and all(m['request_id']=='storage-id' for m in stored)
    assert invalid.status_code==422 and invalid.headers['x-request-id']
    events=records(capsys)
    for forbidden in [QUESTION,ANSWER,SECRET]:
        assert forbidden not in json.dumps(events)
    assert any(e['event']=='conversation_outcome' and e['request_id']=='storage-id' for e in events)
    assert any(e.get('error_code')=='validation_error' for e in events)


def test_duplicate_id_and_cors_short_circuit():
    client=TestClient(create_application())
    r=client.get('/api/v1/health',headers=[('X-Request-ID','one'),('X-Request-ID','two')])
    UUID(r.headers['x-request-id'])
    r=client.options('/api/v1/health',headers={'Origin':'https://example.org',
        'Access-Control-Request-Method':'GET','X-Request-ID':'cors-id'})
    assert r.status_code==400 and r.headers['x-request-id']=='cors-id'


@pytest.mark.asyncio
async def test_provider_failure_is_safe(capsys):
    create_application()
    class FailedLLM:
        async def generate(self, **kwargs):
            raise LLMRequestError(SECRET)
    service=AstaService(rag_service=RAGService(retrieval_service=Retrieval(True),llm_client=FailedLLM()))
    with pytest.raises(LLMRequestError):
        await service.ask(QUESTION)
    events=records(capsys)
    assert any(e.get('stage')=='llm' and e.get('error_code')=='provider_unavailable' for e in events)
    assert SECRET not in json.dumps(events)


@pytest.mark.asyncio
async def test_probe_timeout(monkeypatch):
    import app.core.readiness as readiness
    original=asyncio.timeout
    monkeypatch.setattr(readiness.asyncio,'timeout',lambda seconds: original(.01))
    class Slow(Connection):
        async def execute(self, query):
            await asyncio.sleep(1)
    assert not (await check_readiness(Slow())).ready


def test_404_conversation_category(capsys):
    app=create_application()
    class Service:
        async def send_message(self, **kwargs):
            raise ConversationNotFoundError(kwargs['conversation_id'])
    class Session:
        async def rollback(self): pass
    async def session(): yield Session()
    app.dependency_overrides[get_database_session]=session
    app.dependency_overrides[get_conversation_service]=lambda:Service()
    response=TestClient(app).post(f'/api/v1/chat/conversations/{uuid4()}/messages',json={'message':'Hello'})
    assert response.status_code==404 and response.headers['x-request-id']
    assert response.json()=={'detail':'Conversation was not found.'}
    assert any(e.get('error_code')=='conversation_not_found' for e in records(capsys))


def test_readiness_uses_database_only_and_sanitizes_failure(monkeypatch,capsys):
    import app.core.readiness as readiness
    from app.embeddings.embedding_service import EmbeddingService
    from app.retrieval.reranker import CrossEncoderReranker
    from app.llm.groq_client import GroqLLMClient
    def forbidden(*args, **kwargs):
        raise AssertionError('Forbidden readiness dependency')
    monkeypatch.setattr(EmbeddingService,'_get_encoder',forbidden)
    monkeypatch.setattr(CrossEncoderReranker,'_get_encoder',forbidden)
    monkeypatch.setattr(GroqLLMClient,'generate',forbidden)
    app=create_application()
    monkeypatch.setattr(readiness,'get_engine',lambda:Connection())
    response=TestClient(app).get('/api/v1/ready')
    assert response.status_code==200
    monkeypatch.setattr(readiness,'get_engine',lambda:Connection(fail=True))
    response=TestClient(app).get('/api/v1/ready')
    assert response.status_code==503
    assert SECRET not in response.text
    events=records(capsys)
    assert SECRET not in json.dumps(events)
    assert any(e.get('error_code')=='database_unavailable' for e in events)
