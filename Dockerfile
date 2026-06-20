FROM python:3.11-slim

  WORKDIR /app

  COPY bot/requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  COPY bot/ ./bot/

  # Persistent volume uchun /data papkasini yaratish
  RUN mkdir -p /data

  ENV PYTHONUNBUFFERED=1
  ENV PYTHONPATH=/app/bot

  CMD ["python", "bot/main.py"]
  