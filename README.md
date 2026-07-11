# StrategAI Deployment

StrategAI is an AI-powered e-commerce profit optimization system built with a React + Vite frontend, a FastAPI backend, Supabase PostgreSQL, and Ollama for local LLM tasks.

## Production Targets

- Frontend: Vercel
- Backend: Render
- Database: Supabase PostgreSQL
- LLM: Ollama (configurable host)

## Quick Start

1. Copy `.env.example` to `.env` and fill in the values.
2. Run the local stack:

```bash
docker compose up --build
```

3. Open the frontend at `http://localhost:5173`.
4. Backend health endpoints:

```bash
curl http://localhost:8001/health
curl http://localhost:8001/readiness
curl http://localhost:8001/liveness
```

## Documentation

- [Environment Setup Guide](docs/ENVIRONMENT_SETUP_GUIDE.md)
- [Docker Guide](docs/DOCKER_GUIDE.md)
- [CI/CD Guide](docs/CI_CD_GUIDE.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Cloud Deployment Guide](docs/CLOUD_DEPLOYMENT_GUIDE.md)
