FROM python:3.11-slim

# Force rebuild cache break - v5 - HF Spaces API fix
RUN echo "force rebuild v5 - HF Spaces API endpoint fix"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make app.py executable
RUN chmod +x app.py

# Health check for HF Spaces
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# Hugging Face Spaces require running on port 7860
EXPOSE 7860

# Use app.py as entry point for HF Spaces
CMD ["python", "app.py"]
