FROM python:3.11-slim AS builder
WORKDIR /build
RUN python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel
COPY requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade setuptools wheel
RUN addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 --ingroup app app
COPY --from=builder /venv /venv
COPY --chown=app:app . .
USER app
ENV PATH=/venv/bin:$PATH
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
