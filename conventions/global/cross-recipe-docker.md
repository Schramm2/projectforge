# Docker Cross-Project Defaults

- Use python:3.12-slim base image
- Install uv in the image
- Run as non-root user (adduser --system appuser)
- Include HEALTHCHECK on `/ready` or `/health`
- Single uvicorn worker with `--limit-max-requests 10000`
- EXPOSE 8000
