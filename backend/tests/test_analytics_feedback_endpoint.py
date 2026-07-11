from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


client = TestClient(app)


class FakeAnalyticsDB:
    def __init__(self):
        self.outcome_events = []
        self.workflow_events = []

    def get_analytics_result(self, analytics_result_id):
        if analytics_result_id == 'analytics-1':
            return {
                'id': 'analytics-1',
                'pipeline_run_id': 'run-1',
            }
        return None

    def get_run_recommendations(self, pipeline_run_id):
        if pipeline_run_id == 'run-1':
            return [
                {
                    'id': 'rec-1',
                    'analytics_result_id': 'analytics-1',
                }
            ]
        return []

    def insert_analytics_outcome_event(self, payload):
        event = {'id': 'feedback-1', 'created_at': '2026-07-10T10:00:00Z', **payload}
        self.outcome_events.append(event)
        return event

    def log_workflow_event(self, *args, **kwargs):
        self.workflow_events.append({'args': args, 'kwargs': kwargs})
        return {'id': 1}


def test_submit_feedback_persists_outcome_and_logs_workflow_event():
    fake_db = FakeAnalyticsDB()

    with patch('app.api.analytics.ECDB', return_value=fake_db):
        response = client.post(
            '/analytics/feedback',
            json={
                'analytics_result_id': 'analytics-1',
                'product_name': 'USB C Cable',
                'category': 'accessories',
                'feedback_type': 'acted_on_recommendation',
                'action_taken': 'purchased',
                'actual_buy_price_pkr': 1150,
                'actual_sell_price_pkr': 1499,
                'quantity': 40,
                'notes': 'Closed the loop from the recommended supplier.',
                'source_page': 'results',
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body['id'] == 'feedback-1'
    assert body['pipeline_run_id'] == 'run-1'
    assert body['analytics_result_id'] == 'analytics-1'
    assert body['feedback_type'] == 'acted_on_recommendation'
    assert len(fake_db.outcome_events) == 1
    assert fake_db.outcome_events[0]['recommendation_id'] == 'rec-1'
    assert len(fake_db.workflow_events) == 1
    assert fake_db.workflow_events[0]['args'][1] == 'analytics_feedback_submitted'
