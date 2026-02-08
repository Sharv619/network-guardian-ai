
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if needed
# RUN apt-get update && apt-get install -y gcc

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code into a subdirectory to support 'backend' package imports
COPY . ./backend

# Set PYTHONPATH so python can find the 'backend' package
ENV PYTHONPATH=/app

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
