FROM python:3.12-slim

# Create non-root user and set up instaloader config directory
RUN useradd --create-home appuser \
    && mkdir -p /home/appuser/.config/instaloader \
    && chown -R appuser:appuser /home/appuser/.config/instaloader

# Install from PyPI
RUN pip install --no-cache-dir mcp-instaloader

USER appuser

# Default port (override with MCP_PORT env var)
ENV MCP_PORT=3336

EXPOSE 3336

CMD ["mcp-instaloader"]
