# CI/CD Guide

## Pull Request workflow

The pull request workflow runs:

- backend tests
- backend type/syntax checks
- frontend linting
- frontend TypeScript checks
- frontend production build
- Docker build verification

## Main branch workflow

The main branch workflow repeats the validation steps and then deploys:

- backend via Render deploy hook
- frontend via Vercel deployment

## Required secrets for deployment automation

- `RENDER_DEPLOY_HOOK_URL`
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- Repository variable `VITE_API_BASE_URL` (the production backend URL)
