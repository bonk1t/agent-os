import json
import logging
from typing import Any, Dict, Optional

from e2b_code_interpreter import Sandbox

from backend.settings import settings
from backend.models.skill_config import SkillConfig

logger = logging.getLogger(__name__)

class SandboxManager:
    """Manages E2B sandbox instances for secure tool execution."""
    
    def __init__(self) -> None:
        self.api_key = settings.e2b_api_key
    
    async def execute_skill_from_config(
        self, 
        skill_config: SkillConfig, 
        args: Dict[str, Any], 
        env_vars: Optional[Dict[str, str]] = None
    ) -> str:
        """Execute a skill from its configuration stored in Firestore.
        
        Args:
            skill_config: The SkillConfig object containing the skill code
            args: Arguments to pass to the skill
            env_vars: Optional environment variables for the sandbox
            
        Returns:
            The result of the skill execution
        """
        logger.info(f"Executing skill {skill_config.title} in sandbox")
        
        try:
            # Create a sandbox for each execution using with statement for auto-cleanup
            with Sandbox(api_key=self.api_key) as sandbox:
                # Prepare the sandbox execution code for skill execution
                execution_code = f"""
import json
import os
import sys

print("STEP 1: Starting skill execution in sandbox...")

# Create a simple BaseTool class for the skill to inherit from
class BaseTool:
    \"\"\"Base class for tools.\"\"\"
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# Add OpenAI API key to environment if available
{f'os.environ["OPENAI_API_KEY"] = "{settings.openai_api_key}"' if settings.openai_api_key else ''}

print("STEP 2: Evaluating skill code...")

# Execute the skill code to define the class
{skill_config.content}

print("STEP 3: Looking for skill class...")
# Find all classes that inherit from BaseTool
skill_classes = []
for name, obj in list(globals().items()):
    if (isinstance(obj, type) and 
        obj != BaseTool and 
        issubclass(obj, BaseTool)):
        skill_classes.append((name, obj))
        print(f"  Found skill class: {{name}}")

if not skill_classes:
    print("Error: No skill classes found")
    sys.exit(1)

# Use the first skill class found
skill_class_name, skill_class = skill_classes[0]
print(f"Using skill class: {{skill_class_name}}")

print("STEP 4: Initializing skill with arguments...")
# Parse and prepare arguments
args = {json.dumps(args)}
print(f"  Arguments: {{args}}")

print("STEP 5: Running skill...")
# Execute the skill
try:
    skill_instance = skill_class(**args)
    result = skill_instance.run()
    print("STEP 6: Skill execution complete!")
    print("Output from skill:", result)
except Exception as e:
    error_message = f"Error executing skill: {{e}}"
    print(error_message)
    sys.exit(1)
"""
                
                # Execute the code in the sandbox
                result = sandbox.run_code(execution_code)
                
                # Process the stdout logs to extract the output
                if result.logs and result.logs.stdout:
                    # Join all stdout content - the skill execution result will be in the logs
                    output = ''.join(result.logs.stdout)
                    return output
                else:
                    return "No output from skill execution"
                
        except Exception as e:
            logger.exception(f"Error executing skill {skill_config.title} in sandbox: {e}")
            return f"Error: {str(e)}"


# Global instance
sandbox_manager = SandboxManager() 