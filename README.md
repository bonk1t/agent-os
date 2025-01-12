# Agent OS Platform

Agent OS Platform is an open-source API and web application for managing LLM-driven multi-agent workflows.
Building on OpenAI's Assistants API, it offers a collaborative environment for developing, testing, and deploying AI teams.

## Architecture

### Backend
- FastAPI application for API and WebSocket endpoints
- Firebase Authentication and Firestore for data persistence
- E2B for secure sandbox execution
- Redis for message bus and state management

### Frontend
- Gatsby-based web application
- TailwindCSS for styling
- Ant Design for UI components
- Real-time updates via WebSocket

## Key Features

- **Configuration Management**: Centrally manage configurations for agencies, agents, and skills
- **Custom Skills**: Extend AI agents with specialized skills
- **Secure Execution**: Isolated sandbox environments for running agent code
- **Real-time Communication**: WebSocket support for live updates
- **Modern UI**: Beautiful and responsive interface with best UX practices

## Getting Started

### Quick Start with Docker
1. Create `.env.docker` from `.env.docker.testing` template
2. Run:
   ```bash
   source .env.docker
   FIREBASE_CONFIG=$FIREBASE_CONFIG docker-compose up --build
   ```

### Local Development
1. Backend (FastAPI):
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

2. Frontend (Gatsby):
   ```bash
   cd frontend
   npm install
   yarn start
   ```

For detailed setup instructions, refer to:
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)

## Status

> [!NOTE]
> Agent OS Platform is a research project exploring multi-agent workflows.
