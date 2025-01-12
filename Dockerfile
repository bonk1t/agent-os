FROM node:20.10.0 AS frontend-builder

# Set working directory
WORKDIR /app

# Install rsync
RUN apt-get update && apt-get install -y rsync && rm -rf /var/lib/apt/lists/*

# Copy all package files
COPY build/ build/

# Copy frontend source
COPY frontend/ frontend/

# Create required directories
RUN mkdir -p frontend/src/firebase frontend/static backend/ui

# These environment variables are required for the build
# They should be passed during docker build using --build-arg
ARG FIREBASE_CONFIG
ARG CHATBOT_WIDGET

ENV FIREBASE_CONFIG=${FIREBASE_CONFIG}
ENV CHATBOT_WIDGET=${CHATBOT_WIDGET}

# Run the pre-build script from the correct location
RUN node build/pre-build.js

# Install and build frontend with error handling
RUN cd frontend && \
    npm install -g gatsby-cli && \
    yarn install && \
    yarn build && \
    cp -r public/* ../backend/ui/

# Backend build stage
FROM python:3.13.1-slim

# Set working directory
WORKDIR /app

# Install system dependencies and poetry
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Copy backend code
COPY backend/ backend/

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/backend/ui backend/ui

# Set environment variables
ENV PORT=8000
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "120", "--bind", "0.0.0.0:8000", "backend.main:app"]
