from fastapi.testclient import TestClient

from app.api import health
from app.main import app

client = TestClient(app)


def test_liveness_endpoint_returns_alive():
    response = client.get('/liveness')
    assert response.status_code == 200
    assert response.json()['status'] == 'alive'


def test_readiness_returns_unavailable_when_a_dependency_fails(monkeypatch):
    monkeypatch.setattr(health, 'check_database_readiness', lambda: (False, 'database unavailable'))
    monkeypatch.setattr(health, 'check_ollama_readiness', lambda: (True, 'ollama ready'))

    response = client.get('/readiness')

    assert response.status_code == 503
    payload = response.json()
    assert payload['status'] == 'not_ready'
    assert payload['dependencies']['database']['ready'] is False
    assert payload['dependencies']['ollama']['ready'] is True
