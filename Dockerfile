FROM python:3.12-slim

# Install build tools needed for some dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Create non-root user and set up instaloader config directory
RUN useradd --create-home appuser \
    && mkdir -p /home/appuser/.config/instaloader \
    && chown -R appuser:appuser /home/appuser/.config/instaloader

WORKDIR /app

# Copy project files and install
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

USER appuser

ENV MCP_PORT=3336

EXPOSE 3336

CMD ["mcp-instaloader"]
