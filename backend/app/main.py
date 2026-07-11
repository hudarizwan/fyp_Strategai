from __future__ import annotations

import asyncio
import logging
import os
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.analytics import router as analytics_router
from app.api.health import router as health_router
from app.api.marketing import router as marketing_router
from app.api.reports import router as reports_router
from app.api.scraper import router as scraper_router
from app.core.logging import configure_logging

if os.name == 'nt':
    # Playwright needs a Proactor-based event loop on Windows to spawn subprocesses.
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

configure_logging(os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger('strategai.app')

app = FastAPI(
    title='StrategAI Backend',
    description='AI-based E-Commerce Profit Optimization System',
    version='1.0.0',
)

app.add_middleware(GZipMiddleware, minimum_size=1024)

cors_origins = [origin.strip() for origin in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=['*'],
    allow_headers=['*'],
    allow_credentials=True,
)


@app.middleware('http')
async def request_logging_middleware(request: Request, call_next):
    request_id = uuid4().hex[:12]
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            'request_failed',
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
            },
        )
        raise

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    log_payload = {
        'request_id': request_id,
        'method': request.method,
        'path': request.url.path,
        'status_code': response.status_code,
        'duration_ms': duration_ms,
    }
    if response.status_code >= 500:
        logger.error('request_completed', extra=log_payload)
    elif response.status_code >= 400:
        logger.warning('request_completed', extra=log_payload)
    else:
        logger.info('request_completed', extra=log_payload)
    response.headers['X-Request-Id'] = request_id
    return response


@app.on_event('startup')
def log_startup_configuration() -> None:
    logger.info(
        'strategai_startup',
        extra={
            'service': 'StrategAI Backend',
            'cors_origins': cors_origins,
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'ollama_base_url': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
            'ollama_model': os.getenv('OLLAMA_MODEL', 'llama3.1:8b'),
            'port': int(os.getenv('PORT', '8001')),
            'supabase_url_configured': bool(os.getenv('SUPABASE_URL') or os.getenv('SUPABASE_DB_URL')),
        },
    )


app.include_router(health_router, tags=['Health'])
app.include_router(scraper_router, prefix='/scraper', tags=['Scraper Agent'])
app.include_router(analytics_router, prefix='/analytics', tags=['Analytics Agent'])
app.include_router(marketing_router, prefix='/marketing', tags=['Marketing Agent'])
app.include_router(reports_router, prefix='/reports', tags=['Reports'])
