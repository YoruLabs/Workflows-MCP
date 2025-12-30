FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir mcp requests fastapi uvicorn

# Copy source code
COPY src/ ./src/
COPY workflows/ ./workflows/

# Set environment variables
ENV WORKFLOWS_DIR=/app/workflows
ENV PORT=8000

# Expose port
EXPOSE 8000

# Run the HTTP server
CMD ["python", "src/http_server.py"]
