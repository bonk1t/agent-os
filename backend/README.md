# Backend
[![codecov](https://codecov.io/gh/AI-in-Hand/platform/graph/badge.svg?token=D2ZCM1DK55)](https://codecov.io/gh/AI-in-Hand/platform)


This repository contains the backend implementation of a web application built using FastAPI, a modern,
fast (high-performance), web framework for building APIs with Python. The application provides various functionalities,
including managing agencies, agents, skills, sessions, and user variables.

## Table of Contents

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Custom Skills](#custom-skills)
- [Contributing](#contributing)
- [License](#license)

## Getting Started

These instructions will help you set up the project on your local machine for development and testing purposes.

### Prerequisites

- Python 3.13+
- Pip
- Poetry (for development)
- Google Cloud Platform account
- Firestore database
- Google service account JSON file
- OpenAI API key (set up in the UI)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/AI-in-Hand/platform.git
```

2. Change to the project directory:

```bash
cd platform/backend
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```
or, for development purposes:
```bash
poetry install
```

4. Set up the necessary environment variables (see .env.testing, rename it to .env):

- `GOOGLE_CREDENTIALS`: Contents of the Google service account JSON file (in one line, the command to get it is `cat service-account.json | jq -c .`)
- `ENCRYPTION_KEY`: A key for encrypting and decrypting sensitive data. See `test_encryption_service.py` for key generation.

5. Run the application:

```bash
uvicorn main:app --reload
```

The application will be accessible at `http://localhost:8000`.

## Project Structure

The project is structured as follows:

- `data/agency_data`: Directory for storing agency-specific data.
- `dependencies`: Files related to dependency injection and authentication.
- `models`: Pydantic models representing various entities in the application.
- `routers`: API route definitions for different endpoints.
- `utils`: Utility functions and modules.
- `services`: Service classes and modules for managing different aspects of the application.
- `repositories`: Classes for interacting with the Firestore database.
- `custom_skills`: Custom skill implementations that can be used by agents.

## API Documentation

The API documentation is automatically generated using Swagger UI and can be accessed at `http://localhost:8000/api/docs`
when the application is running.

## Custom Skills

The application supports custom skills that can be used by agents. These skills are defined in the `custom_skills`
directory and include:

- File operations
- Web searches
- Proposal generation
- Code summarization
- And more

To create a new custom skill, add a new Python file in the `custom_skills` directory and define the skill class
following the existing examples.

## Testing

The project uses `pytest` for testing. All tests are located in the `/tests` directory.
To run the tests, execute the following command:
```bash
poetry run pytest
```
