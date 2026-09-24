FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
COPY prompts ./prompts
RUN pip install --no-cache-dir ".[cloud]"

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
ENTRYPOINT ["evalframe"]
