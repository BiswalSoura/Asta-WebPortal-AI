"""Exercise the actual app import/lifespan without network or model construction."""

import socket
import sys
import tomllib
from pathlib import Path
from unittest.mock import patch


def main():
    original_connect = socket.socket.connect

    def blocked(*args, **kwargs):
        raise AssertionError("Startup attempted an external connection")

    def local_socketpair(sock, address):
        # Windows asyncio builds its wakeup socketpair using a loopback TCP connection.
        if isinstance(address, tuple) and address[0] in {'127.0.0.1', '::1'} and address[1] != 5432:
            return original_connect(sock, address)
        return blocked()

    with patch.object(socket.socket, "connect", local_socketpair), patch.object(socket, "create_connection", blocked):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.constants import APP_VERSION
        from app.api.dependencies.services import (
            get_shared_embedding_service, get_shared_reranker, get_shared_llm_client,
        )
        with TestClient(app) as client:
            response = client.get('/api/v1/health', headers={'X-Request-ID': 'ci-startup'})
            assert response.status_code == 200
            assert response.headers['X-Request-ID'] == 'ci-startup'
        assert 'sentence_transformers' not in sys.modules
        assert all(factory.cache_info().currsize == 0 for factory in (
            get_shared_embedding_service, get_shared_reranker, get_shared_llm_client))
        project = tomllib.loads((Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text())
        assert APP_VERSION == project['project']['version'] == app.version
    print('PASS: application import, lifespan, health, request ID and version consistency')


if __name__ == '__main__':
    main()
