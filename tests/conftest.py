import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from backend.settings import settings
from tests.testing_utils import reset_context_vars
from tests.testing_utils.constants import TEST_AGENCY_ID, TEST_AGENT_ID, TEST_ENCRYPTION_KEY, TEST_USER_ID
from tests.testing_utils.mock_firestore_client import MockFirestoreClient

# Configure root logger for tests
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

oai_mock = MagicMock(get_openai_client=MagicMock(return_value=MagicMock(timeout=10)))
sys.modules["agency_swarm.util.oai"] = oai_mock
settings.encryption_key = TEST_ENCRYPTION_KEY
settings.google_credentials = None


@pytest.fixture(autouse=True)
def reset_context_variables():
    """Reset context variables before and after each test."""
    logger.debug("Resetting context variables before test")
    reset_context_vars()
    yield
    logger.debug("Resetting context variables after test")
    reset_context_vars()


@pytest.fixture(autouse=True)
def mock_firestore_client():
    """Provide a mock Firestore client for tests."""
    logger.debug("Setting up mock Firestore client")
    firestore_client = MockFirestoreClient()
    with patch("firebase_admin.firestore.client", return_value=firestore_client):
        yield firestore_client
    logger.debug("Tearing down mock Firestore client")


@pytest.fixture()
def recover_oai_client():
    """Recover the original OAI client and restore mock after test."""
    logger.debug("Recovering original OAI client")
    from . import oai_mock, original_oai_client

    sys.modules["backend.services.oai_client"] = original_oai_client
    yield
    logger.debug("Restoring mock OAI client")
    sys.modules["backend.services.oai_client"] = oai_mock


@pytest.fixture(autouse=True)
def mock_init_oai():
    """Mock OAI initialization."""
    logger.debug("Setting up mock OAI initialization")
    with patch("agency_swarm.Agent.init_oai") as mock:
        yield mock
    logger.debug("Tearing down mock OAI initialization")


skill1 = MagicMock()
skill2 = MagicMock()
skill1.__name__ = "GenerateProposal"
skill2.__name__ = "SearchWeb"
MOCK_SKILL_MAPPING = {"GenerateProposal": skill1, "SearchWeb": skill2}


@pytest.fixture(autouse=True, scope="session")
def mock_skill_mapping():
    """Mock skill mapping for the entire test session."""
    logger.debug("Setting up mock skill mapping")
    with patch("backend.custom_skills.SKILL_MAPPING", MOCK_SKILL_MAPPING):
        yield
    logger.debug("Tearing down mock skill mapping")


@pytest.fixture
def mock_setup_logging():
    """Mock logging configuration."""
    logger.debug("Setting up mock logging configuration")
    with patch("backend.utils.logging_utils.setup_logging"):
        yield
    logger.debug("Tearing down mock logging configuration")


@pytest.fixture
def agency_config_data():
    """Provide test agency configuration data."""
    logger.debug("Creating agency config test data")
    return {
        "id": TEST_AGENCY_ID,
        "user_id": TEST_USER_ID,
        "name": "Test Agency",
        "main_agent": "Sender Agent",
        "agents": [TEST_AGENT_ID],
        "timestamp": "2024-05-05T00:14:57.487901+00:00",
    }


@pytest.fixture
def session_config_data():
    """Provide test session configuration data."""
    logger.debug("Creating session config test data")
    return {
        "id": "test_session_id",
        "user_id": TEST_USER_ID,
        "name": "Test agency",
        "agency_id": TEST_AGENCY_ID,
        "thread_ids": {"main_thread": "test_session_id"},
        "timestamp": "2024-05-05T00:14:57.487901+00:00",
    }


def pytest_sessionstart(session):  # noqa: ARG001
    """Log test session start."""
    logger.info("Starting test session")


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Log test session finish with exit status."""
    logger.info(f"Test session finished with exit status: {exitstatus}")


def pytest_runtest_setup(item):
    """Log individual test setup."""
    logger.info(f"Setting up test: {item.name}")


def pytest_runtest_teardown(item):
    """Log individual test teardown."""
    logger.info(f"Tearing down test: {item.name}")


def pytest_runtest_call(item):
    """Log individual test execution."""
    logger.info(f"Running test: {item.name}")


def pytest_exception_interact(node, call, report):  # noqa: ARG001
    """Log test failures with error details."""
    logger.error(f"Test failed: {node.name}")
    logger.error(f"Error details: {call.excinfo}")
