FROM python:3.11-slim

# Force rebuild cache break - v4 - HF Spaces fix
RUN echo "force rebuild v4 - HF Spaces deployment fix"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Health check for HF Spaces - use proper endpoint
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# Hugging Face Spaces require running on port 7860
EXPOSE 7860

# Start command for HF Spaces - ensure proper binding
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
