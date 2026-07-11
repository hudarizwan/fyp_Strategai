from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ecdb import ECDB


MIGRATION_PATH = Path(__file__).resolve().parents[1] / 'db' / 'migrations' / '005_analytics_model_versions.sql'


def test_model_version_migration_defines_single_active_registry():
    sql = MIGRATION_PATH.read_text(encoding='utf-8')
    assert 'CREATE TABLE IF NOT EXISTS analytics_model_versions' in sql
    assert 'version_tag TEXT NOT NULL' in sql
    assert 'artifact_path TEXT NOT NULL' in sql
    assert 'is_active BOOLEAN NOT NULL DEFAULT false' in sql
    assert 'idx_analytics_model_versions_single_active' in sql


def test_insert_analytics_model_version_deactivates_previous_active_row_in_rest_mode():
    captured: dict[str, object] = {}

    db = ECDB.__new__(ECDB)
    db.driver_name = 'supabase_rest'
    db._new_uuid = lambda: 'version-id-1'

    def fake_rest_patch(table: str, payload, params):
        captured['patch'] = {'table': table, 'payload': payload, 'params': params}
        return []

    def fake_rest_post(table: str, payload):
        captured['post'] = {'table': table, 'payload': payload}
        return [payload]

    db._rest_patch = fake_rest_patch  # type: ignore[assignment]
    db._rest_post = fake_rest_post  # type: ignore[assignment]

    result = db.insert_analytics_model_version(
        {
            'version_tag': 'analytics-pricing-20260710T000000Z',
            'artifact_path': '/tmp/analytics-pricing-20260710T000000Z.joblib',
            'source': 'historical_analytics_results',
            'sample_count': 42,
            'training_metadata': {'source': 'historical_analytics_results'},
            'metrics': {'sample_count': 42},
            'is_active': True,
        }
    )

    assert captured['patch']['table'] == 'analytics_model_versions'
    assert captured['patch']['payload']['is_active'] is False
    assert captured['post']['table'] == 'analytics_model_versions'
    assert captured['post']['payload']['is_active'] is True
    assert result['id'] == 'version-id-1'
    assert result['version_tag'] == 'analytics-pricing-20260710T000000Z'


class _FakeAtomicCursor:
    def __init__(self, connection):
        self.connection = connection
        self.executed = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if 'RETURNING *' in query:
            self.connection.result_row = {
                'id': 'version-id-1',
                'model_name': 'analytics_pricing_model',
                'version_tag': 'analytics-pricing-20260710T000000Z',
                'artifact_path': '/tmp/analytics-pricing-20260710T000000Z.joblib',
                'is_active': True,
                'activated_at': '2026-07-10T00:00:00Z',
            }

    def fetchone(self):
        return getattr(self.connection, 'result_row', None)


class _FakeAtomicConnection:
    def __init__(self):
        self.cursor_calls = 0
        self.commit_calls = 0
        self.result_row = None

    def cursor(self):
        self.cursor_calls += 1
        return _FakeAtomicCursor(self)

    def commit(self):
        self.commit_calls += 1

    def close(self):
        pass


def test_set_active_analytics_model_version_uses_single_transaction_for_direct_db_path():
    db = ECDB.__new__(ECDB)
    db.driver_name = 'psycopg2'
    db.conn = _FakeAtomicConnection()
    db.get_analytics_model_version_by_id = lambda version_id: {
        'id': version_id,
        'model_name': 'analytics_pricing_model',
    }

    result = db.set_active_analytics_model_version('version-id-1')

    assert db.conn.commit_calls == 1
    assert db.conn.cursor_calls == 1
    assert result['id'] == 'version-id-1'
    assert result['is_active'] is True



