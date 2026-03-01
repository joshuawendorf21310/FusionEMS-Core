FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir uv \
    && python3 -c "import tomllib; deps=tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']; open('/tmp/deps.txt','w').write('\n'.join(deps))" \
    && uv pip install --system --no-cache -r /tmp/deps.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "core_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
