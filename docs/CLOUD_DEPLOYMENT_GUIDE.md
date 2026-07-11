# Cloud Deployment Guide

## Render backend

- Use `backend/Dockerfile`
- Health check path: `/readiness`
- Environment variables: use the values from `.env.example`

## Vercel frontend

- Use `frontend/salik-frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Add the Vite environment variables from `.env.example`
- Set `VITE_API_BASE_URL` to the deployed backend URL in your Vercel project or repository variables

## Ollama

StrategAI keeps Ollama configurable through `OLLAMA_BASE_URL`.
Use one of these patterns:

- `http://localhost:11434` for local development
- `http://ollama:11434` for Docker compose
- `https://your-remote-ollama-host` for cloud deployment
