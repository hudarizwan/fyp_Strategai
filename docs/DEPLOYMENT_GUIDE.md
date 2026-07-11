# Deployment Guide

## Recommended setup

- Frontend: Vercel
- Backend: Render
- Database: Supabase PostgreSQL
- Ollama: remote host or Docker compose local stack

## Backend deploy steps on Render

1. Create a new Web Service from the repository. If you are using the monorepo checkout, make sure submodules are fetched recursively so `frontend/salik-frontend` is available.
2. Point Render at `backend/Dockerfile`.
3. Set the health check path to `/readiness`.
4. Add the required environment variables from `.env.example`.
5. Set `OLLAMA_BASE_URL` to a reachable Ollama server. Render will inject the service `PORT`; do not hardcode a fixed port in the service settings.
6. Deploy.

## Frontend deploy steps on Vercel

1. Import the frontend project from `frontend/salik-frontend`. If cloning manually, run `git submodule update --init --recursive` first so the frontend files are present.
2. Set the framework to Vite if prompted.
3. Add the Vite environment variables from `.env.example`.
4. Deploy.

## Local smoke checks

```bash
curl http://localhost:8001/health
curl http://localhost:8001/readiness
curl http://localhost:8001/liveness
```