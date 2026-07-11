# Deployment Guide

## Recommended setup

- Frontend: Vercel
- Backend: Render
- Database: Supabase PostgreSQL
- Ollama: remote host or Docker compose local stack

## Backend deploy steps on Render

1. Create a new Web Service from the repository.
2. Point Render at `backend/Dockerfile`.
3. Set the health check path to `/readiness`.
4. Add the required environment variables from `.env.example`.
5. Set `OLLAMA_BASE_URL` to a reachable Ollama server.
6. Deploy.

## Frontend deploy steps on Vercel

1. Import the frontend project from `frontend/salik-frontend`.
2. Set the framework to Vite if prompted.
3. Add the Vite environment variables from `.env.example`.
4. Deploy.

## Local smoke checks

```bash
curl http://localhost:8001/health
curl http://localhost:8001/readiness
curl http://localhost:8001/liveness
```
