# Deployment Guide

Agent Airlock is designed to run either as a unified single-container deployment (where FastAPI serves both the API and the static Next.js export) or as separate frontend and backend deployments.

## Architecture

In the unified deployment:
- Node builds the Next.js frontend into static assets (`frontend/out`).
- Python runs the FastAPI server on port 8000.
- FastAPI routes `/api/*` and `/healthz` to its API handlers, and serves the Next.js static pages for all UI routes (`/`, `/attacks`, `/events`, `/policies`, `/investigations`).
- All browser network requests are relative same-origin calls, eliminating CORS issues and preserving server-sent event (SSE) streaming.

## 1. Local Container Deployment (Docker)

Build and run using Docker:

```sh
# Build unified image
docker build -t agent-airlock .

# Run with persistent volume for SQLite audit storage
docker run --rm -p 8000:8000 \
  --env-file backend/.env \
  -e DATABASE_URL=sqlite:////app/data/airlock.db \
  -v airlock-data:/app/data \
  agent-airlock
```

Then visit `http://localhost:8000` in your browser.

## 2. Cloud Deployment (Render / Railway / Fly.io)

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `CLOCKED_API_KEY` | Yes | Your live Clocked API key (`clk_live_...`) |
| `AIRLOCK_MODE` | Yes | Must be `live` |
| `DATABASE_URL` | Yes | e.g. `sqlite:////app/data/airlock.db` with a mounted persistent volume |
| `AIRLOCK_REVIEW_TOKEN` | Optional | Shared bearer secret for reviewer approvals (`/api/reviews/*`) |
| `PORT` | Auto | The port assigned by the container host (default `8000`) |

### Critical Requirements for Cloud Hosts

1. **Persistent Disk**: SQLite WAL mode requires persistent disk storage (e.g., `/app/data`) so audit logs and runs persist across redeploys.
2. **Server-Sent Events (SSE)**: Ensure your proxy or load balancer does not buffer responses (disable response buffering for `/api/runs/*/events`). FastAPI automatically sends `X-Accel-Buffering: no` and periodic heartbeats.
3. **No Client-Side Secrets**: Never set `NEXT_PUBLIC_CLOCKED_API_KEY`. The frontend communicates only with FastAPI.
