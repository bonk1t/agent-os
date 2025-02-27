# Agent OS Development Guide

## Commands
- **Backend**: `cd backend && poetry install && uvicorn main:app --reload`
- **Frontend**: `cd frontend && npm install && yarn start`
- **Testing**: `cd backend && poetry run pytest`
- **Single Test**: `cd backend && poetry run pytest tests/path/to/test_file.py::TestClass::test_method -v`
- **Linting**: `cd backend && poetry run ruff check .`
- **Typecheck**: `cd frontend && npm run typecheck` or `cd backend && pyright`
- **E2B Test**: `cd backend && poetry run python basic_e2b_test.py`

## Style Guidelines
- **Python**: 120 char line length, Python 3.13+, async OpenAI calls, type hints required
- **Imports**: Use isort (combined-as-imports=true)
- **Formatting**: Ruff for Python, follow existing conventions in TypeScript/React
- **Error Handling**: Proper exception handling with FastAPI exception handlers
- **Architecture**: Follow design principles in .cursorrules - simplicity, security, maintainability
- **Security**: Isolated execution in E2B sandboxes, validate all tools, use Firebase Authentication
- **State Management**: Use Redis for message bus and state management
- **Testing**: High test coverage required, both unit and integration tests

## Sandbox Execution
- All skill code is stored in Firestore and executed in isolated E2B sandboxes
- E2B API key must be set in .env: `E2B_API_KEY=your_key`
- Each skill execution creates a fresh sandbox that is destroyed immediately after
- Use `SandboxManager` class for secure code execution
- Skills must inherit from `BaseTool` to be discovered and executed