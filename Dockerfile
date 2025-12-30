FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir mcp requests pyyaml fastapi uvicorn sse-starlette

# Copy source code
COPY src/ ./src/
COPY skills/ ./skills/

# Set environment variables
ENV SKILLS_DIR=/app/skills
ENV PORT=8000

# Expose port
EXPOSE 8000

# Run the HTTP server (for Railway/remote deployment)
# For local MCP usage, run: skills-mcp
CMD ["python", "src/mcp_http_server.py"]
