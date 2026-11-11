# Single-service image: the API also serves the built web app.
# Used by render.yaml (free hosting) and works on any Docker host that sets $PORT.
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STATIC_DIR=/app/static PORT=8000
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=web /web/dist /app/static
RUN useradd -m aaroh && mkdir -p /data/uploads && chown -R aaroh /data /app
USER aaroh
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && if [ \"$SEED_DEMO\" = \"true\" ]; then python -m app.seed --if-missing; fi && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
