# Base image
FROM python:3.12-slim-bullseye

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1  
ENV PYTHONUNBUFFERED=1

# Install uv
RUN pip install uv

# Set the working directory
WORKDIR /app

# Copy only dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# adding venv's bin to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy the rest of the application code
COPY . .

# Copy entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose the port the app runs on
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Start server using Gunicorn with Uvicorn workers (Best of both worlds: workers + ASGI)
CMD ["gunicorn", "core.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]