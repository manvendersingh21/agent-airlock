FROM node:22-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 AIRLOCK_MODE=live PORT=8000
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/
COPY fixtures/ /app/fixtures/
COPY --from=frontend /app/frontend/out/ /app/frontend/out/
RUN useradd --create-home airlock && mkdir -p /app/data && chown -R airlock:airlock /app
USER airlock
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]
