# Docker Deployment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Dockerize BiliInsight for one-command deployment: `docker compose up`

**Architecture:** 3 containers — FastAPI (uvicorn, port 8080), PostgreSQL 16, nginx (serves frontend static files + proxies /api → api:8080)

**Tech Stack:** Docker, docker-compose, nginx, Python 3.13-slim

---

### Task 1: Dockerfile for API

**Files:**
- Create: `Dockerfile`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

# Copy source
COPY src/ ./src/
COPY app/ ./app/
COPY config.example.yaml ./config.yaml

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "api.app:create_app", "--host", "0.0.0.0", "--port", "8080", "--factory"]
```

### Task 2: nginx config

**Files:**
- Create: `nginx.conf`

```nginx
server {
    listen 80;
    server_name localhost;

    # Frontend static files
    root /usr/share/nginx/html;
    index index.html;

    # API proxy
    location /api/ {
        proxy_pass http://api:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### Task 3: docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-biliinsight}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-biliinsight}
      POSTGRES_DB: ${POSTGRES_DB:-biliinsight}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-biliinsight}"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-biliinsight}:${POSTGRES_PASSWORD:-biliinsight}@db:5432/${POSTGRES_DB:-biliinsight}
      BILI_CONFIG_PATH: /app/config.yaml
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
      - ./config.yaml:/app/config.yaml:ro

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./app/ui/dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - api

volumes:
  pgdata:
```

### Task 4: .env.example + .dockerignore + .gitignore update

**Files:**
- Create: `.env.example`
- Create: `.dockerignore`

```bash
# .env.example
POSTGRES_USER=biliinsight
POSTGRES_PASSWORD=biliinsight
POSTGRES_DB=biliinsight
```

```dockerignore
# .dockerignore
__pycache__/
*.pyc
.venv/
.git/
.pytest_cache/
.mypy_cache/
app/ui/node_modules/
app/ui/src/
app/ui/e2e/
app/ui/design-demos/
data/
*.md
docs/
```

### Task 5: Verify Build

- [ ] Build frontend: `cd app/ui && pnpm build`
- [ ] Build Docker image: `docker build -t biliinsight-api .`
- [ ] Verify docker compose: `docker compose config`
- [ ] Commit all files

### Task 6: Commit

```bash
git add Dockerfile docker-compose.yml nginx.conf .env.example .dockerignore .gitignore
git commit -m "feat: Docker deployment — 3-service docker compose"
```
