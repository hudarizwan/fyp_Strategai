from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.services.ecdb import ECDB


client = TestClient(app)


class FakeHistoryDB:
    def get_price_history(self, product_name: str, category: str, limit: int = 12):
        assert product_name == 'USB C Cable'
        assert category == 'accessories'
        assert limit == 12
        return [
            {
                'pipeline_run_id': 'run-1',
                'captured_at': '2026-07-01T10:00:00Z',
                'wholesale_count': 2,
                'retail_count': 2,
                'wholesale_avg_price_pkr': 110.0,
                'wholesale_min_price_pkr': 100.0,
                'wholesale_max_price_pkr': 120.0,
                'retail_avg_price_pkr': 155.0,
                'retail_min_price_pkr': 150.0,
                'retail_max_price_pkr': 160.0,
            }
        ]


def test_get_price_history_groups_raw_rows_by_pipeline_run():
    db = ECDB.__new__(ECDB)
    db.driver_name = 'supabase_rest'

    wholesale_rows = [
        {'pipeline_run_id': 'run-1', 'captured_at': '2026-07-01T10:00:00Z', 'raw_price': 100},
        {'pipeline_run_id': 'run-1', 'captured_at': '2026-07-01T10:00:00Z', 'raw_price': 120},
        {'pipeline_run_id': 'run-2', 'captured_at': '2026-07-10T10:00:00Z', 'raw_price': 110},
    ]
    retail_rows = [
        {'pipeline_run_id': 'run-1', 'captured_at': '2026-07-01T10:00:00Z', 'raw_price': 150},
        {'pipeline_run_id': 'run-1', 'captured_at': '2026-07-01T10:00:00Z', 'raw_price': 160},
        {'pipeline_run_id': 'run-2', 'captured_at': '2026-07-10T10:00:00Z', 'raw_price': 170},
    ]

    def fake_rest_get(table: str, params):
        if table == 'raw_wholesale_records':
            return wholesale_rows
        if table == 'raw_retail_records':
            return retail_rows
        raise AssertionError(f'unexpected table: {table}')

    db._rest_get = fake_rest_get  # type: ignore[assignment]

    points = db.get_price_history('USB C Cable', 'accessories', limit=12)

    assert len(points) == 2
    assert points[0]['pipeline_run_id'] == 'run-1'
    assert points[0]['wholesale_avg_price_pkr'] == 110.0
    assert points[0]['retail_avg_price_pkr'] == 155.0
    assert points[1]['pipeline_run_id'] == 'run-2'
    assert points[1]['wholesale_count'] == 1
    assert points[1]['retail_count'] == 1


def test_price_history_endpoint_returns_grouped_points():
    fake_db = FakeHistoryDB()

    with patch('app.api.analytics.ECDB', return_value=fake_db):
        response = client.get('/analytics/price-history', params={'product_name': 'USB C Cable', 'category': 'accessories'})

    assert response.status_code == 200
    body = response.json()
    assert body['product_name'] == 'USB C Cable'
    assert body['category'] == 'accessories'
    assert body['total_points'] == 1
    assert body['points'][0]['pipeline_run_id'] == 'run-1'
