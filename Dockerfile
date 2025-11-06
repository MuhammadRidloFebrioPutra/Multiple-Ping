FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libssl-dev \
       libffi-dev \
       git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . /app

EXPOSE 5000

# Use Gunicorn with gevent worker for concurrency
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app", "--workers", "3", "--worker-class", "gevent", "--timeout", "120"]
