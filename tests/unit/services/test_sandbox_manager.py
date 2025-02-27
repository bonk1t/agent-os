import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from backend.models.skill_config import SkillConfig
from backend.services.sandbox_manager import SandboxManager


@pytest_asyncio.fixture
async def mock_e2b_sandbox():
    with patch("backend.services.sandbox_manager.Sandbox") as mock_sandbox_class:
        mock_sandbox = AsyncMock()
        mock_sandbox.run_code = AsyncMock(return_value=MagicMock(text="Sandbox execution result"))
        mock_sandbox.process = AsyncMock()
        mock_sandbox.process.set_env = AsyncMock()
        mock_sandbox.close = AsyncMock()
        
        mock_sandbox_class.create = AsyncMock(return_value=mock_sandbox)
        yield mock_sandbox, mock_sandbox_class


@pytest_asyncio.fixture
async def mock_code_interpreter_sandbox():
    with patch("backend.services.sandbox_manager.CodeInterpreterSandbox") as mock_sandbox_class:
        mock_sandbox = MagicMock()
        
        mock_sandbox_class.return_value = mock_sandbox
        yield mock_sandbox, mock_sandbox_class


@pytest.fixture
def mock_settings():
    with patch("backend.services.sandbox_manager.settings") as mock_settings:
        mock_settings.e2b_api_key = "test_api_key"
        mock_settings.e2b_sandbox_timeout = 300
        mock_settings.e2b_sandbox_memory = 512
        mock_settings.e2b_sandbox_cpu = 0.5
        mock_settings.openai_api_key = "test_openai_key"
        yield mock_settings


@pytest.mark.asyncio
async def test_create_sandbox(mock_e2b_sandbox, mock_settings):
    _, mock_sandbox_class = mock_e2b_sandbox
    
    sandbox_manager = SandboxManager()
    await sandbox_manager.create_sandbox()
    
    mock_sandbox_class.create.assert_called_once_with(
        api_key="test_api_key",
        timeout=300,
        memory=512,
        cpu=0.5
    )


@pytest.mark.asyncio
async def test_create_code_interpreter_sandbox(mock_code_interpreter_sandbox, mock_settings):
    _, mock_sandbox_class = mock_code_interpreter_sandbox
    
    sandbox_manager = SandboxManager()
    sandbox_manager.create_code_interpreter_sandbox()
    
    mock_sandbox_class.assert_called_once_with(
        api_key="test_api_key",
        timeout_seconds=300,
        memory_mb=512,
        cpu=0.5
    )


@pytest.mark.asyncio
async def test_execute_code(mock_e2b_sandbox, mock_settings):
    mock_sandbox, _ = mock_e2b_sandbox
    code = "print('Hello World')"
    env_vars = {"TEST_VAR": "test_value"}
    
    sandbox_manager = SandboxManager()
    result = await sandbox_manager.execute_code(mock_sandbox, code, env_vars)
    
    mock_sandbox.process.set_env.assert_called_once_with("TEST_VAR", "test_value")
    mock_sandbox.run_code.assert_called_once_with(code)
    assert result == "Sandbox execution result"


@pytest.mark.asyncio
async def test_cleanup_sandbox(mock_e2b_sandbox):
    mock_sandbox, _ = mock_e2b_sandbox
    
    sandbox_manager = SandboxManager()
    await sandbox_manager.cleanup_sandbox(mock_sandbox)
    
    mock_sandbox.close.assert_called_once()


@pytest.mark.asyncio
async def test_execute_tool(mock_e2b_sandbox, mock_settings):
    mock_sandbox, mock_sandbox_class = mock_e2b_sandbox
    
    tool_code = "print('Hello from tool')"
    tool_args = {"arg1": "value1", "arg2": "value2"}
    env_vars = {"TEST_VAR": "test_value"}
    
    sandbox_manager = SandboxManager()
    result = await sandbox_manager.execute_tool(tool_code, tool_args, env_vars)
    
    # Verify sandbox was created and cleaned up
    mock_sandbox_class.create.assert_called_once()
    mock_sandbox.close.assert_called_once()
    
    # Verify setup code was executed with tool args
    setup_call_args = mock_sandbox.run_code.call_args_list[0][0][0]
    assert "tool_args = json.loads('" in setup_call_args
    assert json.dumps(tool_args) in setup_call_args
    
    # Verify tool code was executed
    mock_sandbox.run_code.assert_any_call(tool_code)
    
    # Verify environment variables were set
    mock_sandbox.process.set_env.assert_called_with("TEST_VAR", "test_value")
    
    assert result == "Sandbox execution result"


@pytest.fixture
def mock_skill_config():
    return SkillConfig(
        id="skill1",
        user_id="user1", 
        title="TestSkill",
        description="Test skill for unit tests",
        content="class TestSkill(BaseTool):\n    def run(self):\n        return 'Success'"
    )


@pytest.mark.asyncio
async def test_execute_skill_from_config(mock_e2b_sandbox, mock_settings, mock_skill_config):
    mock_sandbox, mock_sandbox_class = mock_e2b_sandbox
    args = {"arg1": "value1"}
    env_vars = {"TEST_VAR": "test_value"}
    
    sandbox_manager = SandboxManager()
    result = await sandbox_manager.execute_skill_from_config(mock_skill_config, args, env_vars)
    
    # Verify sandbox was created and cleaned up
    mock_sandbox_class.create.assert_called_once()
    mock_sandbox.close.assert_called_once()
    
    # Verify environment variables were set (including OpenAI API key)
    mock_sandbox.process.set_env.assert_any_call("TEST_VAR", "test_value")
    mock_sandbox.process.set_env.assert_any_call("OPENAI_API_KEY", "test_openai_key")
    
    # Verify execution code was executed with skill content and args
    execution_call_args = mock_sandbox.run_code.call_args[0][0]
    assert mock_skill_config.content in execution_call_args
    assert "tool_class = find_tool_class()" in execution_call_args
    assert json.dumps(args) in execution_call_args
    
    assert result == "Sandbox execution result"


@pytest.mark.asyncio
async def test_execute_skill_from_config_exception_handling(mock_e2b_sandbox, mock_skill_config):
    mock_sandbox, mock_sandbox_class = mock_e2b_sandbox
    
    # Make the sandbox raise an exception
    error_msg = "Sandbox execution failed"
    mock_sandbox.run_code.side_effect = Exception(error_msg)
    
    sandbox_manager = SandboxManager()
    result = await sandbox_manager.execute_skill_from_config(mock_skill_config, {})
    
    # Verify sandbox was created and cleaned up even with the error
    mock_sandbox_class.create.assert_called_once()
    mock_sandbox.close.assert_called_once()
    
    # Verify error is returned properly
    assert f"Error: {error_msg}" in result