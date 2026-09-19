# syntax=docker/dockerfile:1

FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install \
    --prefer-binary \
    --only-binary=:all: \
    --timeout 120 \
    --retries 5 \
    --index-url https://pypi.org/simple \
    -r requirements.txt \
    && python -m pip install \
    --prefer-binary \
    --only-binary=:all: \
    email-validator

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install \
    --prefer-binary \
    --only-binary=:all: \
    --timeout 120 \
    --retries 5 \
    torch==2.14.0 \
    --index-url https://download.pytorch.org/whl/cpu

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]