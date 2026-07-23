FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY ai /app/ai
RUN python -m pip install --upgrade pip \
    && python -m pip install -e /app/ai

WORKDIR /app/ai

CMD ["python", "-m", "compileall", "bitonx_ai"]
