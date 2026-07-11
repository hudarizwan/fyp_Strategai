from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ecdb import ECDB


MIGRATION_PATH = Path(__file__).resolve().parents[1] / 'db' / 'migrations' / '006_mcb_category_thresholds.sql'


def test_mcb_threshold_migration_defines_threshold_and_audit_tables():
    sql = MIGRATION_PATH.read_text(encoding='utf-8')
    assert 'CREATE TABLE IF NOT EXISTS mcb_category_thresholds' in sql
    assert 'approval_confidence_threshold NUMERIC(4,3) NOT NULL CHECK' in sql
    assert 'changed_by TEXT NOT NULL DEFAULT' in sql
    assert 'CREATE TABLE IF NOT EXISTS mcb_threshold_audit_events' in sql
    assert 'new_approval_confidence_threshold NUMERIC(4,3) NOT NULL CHECK' in sql


def test_set_mcb_category_threshold_writes_threshold_and_audit_rows_atomically():
    class FakeCursor:
        def __init__(self, connection):
            self.connection = connection
            self.results = []
            self.executed = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.executed.append((query, params))
            self.connection.statements.append((query, params))
            if query.strip().startswith('SELECT id, approval_confidence_threshold'):
                self.results = []
            elif 'INSERT INTO mcb_category_thresholds' in query:
                self.results = [{
                    'id': 'threshold-id-1',
                    'category': params[0],
                    'approval_confidence_threshold': params[1],
                    'changed_by': params[2],
                    'change_reason': params[3],
                }]
            elif 'UPDATE mcb_category_thresholds' in query:
                self.results = [{
                    'id': 'threshold-id-1',
                    'category': 'headset',
                    'approval_confidence_threshold': params[0],
                    'changed_by': params[1],
                    'change_reason': params[2],
                }]
            elif 'INSERT INTO mcb_threshold_audit_events' in query:
                self.results = [{
                    'id': 'audit-id-1',
                }]

        def fetchone(self):
            if not self.results:
                return None
            return self.results.pop(0)

    class FakeConn:
        def __init__(self):
            self.statements = []
            self.commit_calls = 0

        def cursor(self):
            return FakeCursor(self)

        def commit(self):
            self.commit_calls += 1

        def close(self):
            pass

    db = ECDB.__new__(ECDB)
    db.driver_name = 'psycopg2'
    db.conn = FakeConn()

    row = db.set_mcb_category_threshold(
        category='headset',
        approval_confidence_threshold=0.83,
        changed_by='system:threshold-script',
        change_reason='Tighter approval for thin-headset data.',
        source_script='set_mcb_category_threshold.py',
    )

    assert db.conn.commit_calls == 1
    assert any('INSERT INTO mcb_category_thresholds' in statement[0] for statement in db.conn.statements)
    assert any('INSERT INTO mcb_threshold_audit_events' in statement[0] for statement in db.conn.statements)
    assert row['category'] == 'headset'
    assert row['approval_confidence_threshold'] == 0.83



def test_mcb_completed_workflow_event_includes_threshold_provenance():
    class FakeDB:
        def __init__(self):
            self.workflow_events = []
            self.queries = []

        def create_agent_execution(self, *args, **kwargs):
            return {'id': 'mcb-exec-1'}

        def finalize_agent_execution(self, *args, **kwargs):
            return {'id': 'mcb-exec-1'}

        def log_workflow_event(self, *args, **kwargs):
            self.workflow_events.append({'args': args, 'kwargs': kwargs})
            return {'id': 'workflow-1'}

        def create_pipeline_run(self, *args, **kwargs):
            return {'id': 'run-1'}

        def finalize_pipeline_run(self, *args, **kwargs):
            return {'id': 'run-1'}

        def insert_recommendation(self, payload):
            return {'id': 1}

        def get_effective_mcb_confidence_threshold(self, category):
            return 0.81

        def resolve_mcb_confidence_threshold(self, category):
            return {
                'confidence_threshold': 0.81,
                'threshold_source_tier': 'exact category',
                'threshold_source_category': category,
            }

    db = FakeDB()
    from app.services.mcb_decision_agent import MCBDecisionAgent
    agent = MCBDecisionAgent(db=db)
    from app.services.mcb_models import MCBDecisionInput, MarketStats, AnalyticsOutput, CompetitorSignals, MarketingOutput
    payload = MCBDecisionInput(
        product_name='HyperX Cloud III',
        category='headset',
        wholesale=MarketStats(avg_price_pkr=2800, min_price_pkr=2600, max_price_pkr=3200, participant_count=4),
        retail=MarketStats(avg_price_pkr=3900, min_price_pkr=3600, max_price_pkr=4300, participant_count=5),
        analytics=AnalyticsOutput(predicted_price_pkr=3850, predicted_margin_percent=27, confidence_score=0.82),
        competitors=CompetitorSignals(discount_intensity='medium', stock_out_rate=0.08, price_aggression='medium'),
        marketing=MarketingOutput(segment='value gamers', positioning='Trusted gaming headset with proof-led comfort messaging.', primary_channel='daraz', budget_pkr=18000, expected_roi_percent=46, confidence_score=0.79),
    )
    decision = agent.decide(payload)
    from app.api.analytics import _build_mcb_workflow_metadata
    metadata = _build_mcb_workflow_metadata(decision)
    assert metadata['threshold_source_tier'] == 'exact category'
    assert metadata['confidence_threshold'] == 0.81
