from __future__ import annotations

import logging
import os
import time
from typing import Dict, Tuple
from urllib.parse import urlparse

import requests
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config.supabase_config import SUPABASE_DB_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, SUPABASE_URL

try:
    import pg8000.native as pg8000_native
except Exception:  # pragma: no cover - optional dependency fallback
    pg8000_native = None

try:
    import psycopg2
except Exception:  # pragma: no cover - optional dependency fallback
    psycopg2 = None

router = APIRouter()
logger = logging.getLogger('strategai.health')
STARTED_AT = time.monotonic()
HEALTH_TIMEOUT_SECONDS = float(os.getenv('HEALTHCHECK_TIMEOUT_SECONDS', '3'))
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434').rstrip('/')


def _connection_mode() -> str:
    if SUPABASE_DB_URL:
        return 'postgres'
    if SUPABASE_URL and (SUPABASE_SERVICE_KEY or SUPABASE_KEY):
        return 'rest'
    return 'unconfigured'


def check_database_readiness() -> Tuple[bool, str]:
    mode = _connection_mode()
    if mode == 'unconfigured':
        return False, 'Supabase database configuration is missing'

    if mode == 'postgres':
        if psycopg2 is not None:
            try:
                conn = psycopg2.connect(SUPABASE_DB_URL, connect_timeout=2)
                try:
                    with conn.cursor() as cursor:
                        cursor.execute('SELECT 1')
                        cursor.fetchone()
                finally:
                    conn.close()
                return True, 'PostgreSQL connection healthy'
            except Exception as exc:  # pragma: no cover - depends on external DB state
                logger.warning('database readiness probe failed', extra={'error': str(exc)})
                return False, f'PostgreSQL connection failed: {exc}'

        if pg8000_native is not None:
            try:
                parsed = urlparse(SUPABASE_DB_URL)
                conn = pg8000_native.Connection(
                    user=parsed.username,
                    password=parsed.password,
                    host=parsed.hostname,
                    port=parsed.port or 5432,
                    database=(parsed.path or '/postgres').lstrip('/'),
                    ssl_context=True,
                    timeout=2,
                )
                try:
                    conn.run('SELECT 1')
                finally:
                    conn.close()
                return True, 'PostgreSQL connection healthy'
            except Exception as exc:  # pragma: no cover - depends on external DB state
                logger.warning('database readiness probe failed', extra={'error': str(exc)})
                return False, f'PostgreSQL connection failed: {exc}'

        return False, 'No PostgreSQL driver available for readiness probe'

    try:
        response = requests.get(
            f'{SUPABASE_URL.rstrip("/")}/rest/v1/',
            headers={
                'apikey': SUPABASE_SERVICE_KEY or SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_KEY or SUPABASE_KEY}',
            },
            timeout=HEALTH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return True, 'Supabase REST endpoint healthy'
    except Exception as exc:  # pragma: no cover - depends on external REST state
        logger.warning('database readiness probe failed', extra={'error': str(exc)})
        return False, f'Supabase REST endpoint failed: {exc}'


def check_ollama_readiness() -> Tuple[bool, str]:
    try:
        response = requests.get(f'{OLLAMA_BASE_URL}/api/tags', timeout=HEALTH_TIMEOUT_SECONDS)
        response.raise_for_status()
        return True, 'Ollama healthy'
    except Exception as exc:  # pragma: no cover - depends on external service state
        logger.warning('ollama readiness probe failed', extra={'error': str(exc)})
        return False, f'Ollama unavailable: {exc}'


@router.get('/health')
def health() -> JSONResponse:
    database_ready, database_reason = check_database_readiness()
    ollama_ready, ollama_reason = check_ollama_readiness()
    overall_ready = database_ready and ollama_ready
    payload = {
        'status': 'ok' if overall_ready else 'degraded',
        'service': 'StrategAI Backend',
        'uptime_seconds': round(time.monotonic() - STARTED_AT, 2),
        'dependencies': {
            'database': {'ready': database_ready, 'reason': database_reason},
            'ollama': {'ready': ollama_ready, 'reason': ollama_reason},
        },
    }
    return JSONResponse(status_code=200 if overall_ready else 503, content=payload)


@router.get('/liveness')
def liveness() -> Dict[str, str]:
    return {'status': 'alive', 'service': 'StrategAI Backend'}


@router.get('/readiness')
def readiness() -> JSONResponse:
    database_ready, database_reason = check_database_readiness()
    ollama_ready, ollama_reason = check_ollama_readiness()
    overall_ready = database_ready and ollama_ready
    payload = {
        'status': 'ready' if overall_ready else 'not_ready',
        'dependencies': {
            'database': {'ready': database_ready, 'reason': database_reason},
            'ollama': {'ready': ollama_ready, 'reason': ollama_reason},
        },
    }
    return JSONResponse(status_code=200 if overall_ready else 503, content=payload)
