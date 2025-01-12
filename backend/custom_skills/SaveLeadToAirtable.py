import logging

from agency_swarm import BaseTool
from pyairtable import Api
from pydantic import Field

from backend.repositories.agent_flow_spec_storage import AgentFlowSpecStorage
from backend.repositories.user_variable_storage import UserVariableStorage
from backend.services.user_variable_manager import UserVariableManager

logger = logging.getLogger(__name__)


class SaveLeadToAirtable(BaseTool):
    """Save a new lead to Airtable."""

    name: str = Field(..., description="Name of the new potential client.")
    email: str = Field(..., description="Email of the new potential client.")
    lead_details: str = Field(..., description="Lead details.")

    def run(self) -> str:
        """Save a new lead to Airtable."""
        user_variable_manager = UserVariableManager(UserVariableStorage(), AgentFlowSpecStorage())

        try:
            airtable_base_id = user_variable_manager.get_by_key("AIRTABLE_BASE_ID")
            airtable_table_id = user_variable_manager.get_by_key("AIRTABLE_TABLE_ID")
            airtable_token = user_variable_manager.get_by_key("AIRTABLE_TOKEN")

            api = Api(airtable_token)
            table = api.table(airtable_base_id, airtable_table_id)

            data = {
                "Name": self.name,
                "Email": self.email,
                "Lead Details": self.lead_details,
            }

            response = table.create(data)
            airtable_message = f"Response from Airtable: id: {response['id']}, createdTime: {response['createdTime']}"
        except Exception as e:
            airtable_message = f"Error while saving lead to Airtable: {e}"
            logger.exception(airtable_message)

        return airtable_message
