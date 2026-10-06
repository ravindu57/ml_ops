# Build stage instructions run at image build time.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Dependencies first so the layer caches while only source files change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY train.py .
COPY app.py .

# Build-time training: iris_model.joblib is created INSIDE the image.
RUN python train.py

EXPOSE 5000

# Startup configuration only: what runs when a container starts.
CMD ["python", "app.py"]