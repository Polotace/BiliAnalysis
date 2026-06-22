FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

COPY src/ ./src/
COPY app/ ./app/
COPY config.example.yaml ./config.yaml

EXPOSE 8080

CMD ["uv", "run", "bilianalysis", "serve", "--port", "8080"]
