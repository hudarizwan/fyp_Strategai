# Docker Guide

## Build and run the full stack

```bash
docker compose up --build
```

## Build images manually

Backend:

```bash
docker build -t strategai-backend ./backend
```

Frontend:

```bash
docker build -t strategai-frontend ./frontend/salik-frontend
```

## Health endpoints

- Backend: `http://localhost:8001/health`
- Frontend: `http://localhost:5173/health`
