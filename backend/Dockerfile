FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps for cryptography/reportlab fonts
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

COPY . /app

EXPOSE 8000
CMD ["uvicorn", "core_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
