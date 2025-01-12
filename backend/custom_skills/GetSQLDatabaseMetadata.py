"""
To use this skill, you need to set the DATABASE_URL_PREFIX and DATABASE_PASSWORD user variables.
The DATABASE_URL_PREFIX should follow the appropriate format for the specific database type [supported DBMSs],
excluding the database name:
- PostgreSQL: postgresql://username@host:port/
- MySQL: mysql://username@host:port/
- Oracle: oracle://username@host:port/
"""

import json
import logging

from agency_swarm import BaseTool
from pydantic import Field
from sqlalchemy import MetaData, create_engine

from backend.repositories.agent_flow_spec_storage import AgentFlowSpecStorage
from backend.repositories.user_variable_storage import UserVariableStorage
from backend.services.user_variable_manager import UserVariableManager

logger = logging.getLogger(__name__)


class GetSQLDatabaseMetadata(BaseTool):
    """Get metadata (tables and columns) from a SQL database using SQLAlchemy."""

    database_name: str = Field(..., description="Database name (for PostgreSQL, MySQL) or SID (for Oracle).")

    def run(self) -> str:
        """Execute the SQL query and return the result as a formatted string."""
        user_variable_manager = UserVariableManager(UserVariableStorage(), AgentFlowSpecStorage())
        database_url_prefix = user_variable_manager.get_by_key("DATABASE_URL_PREFIX")
        database_password = user_variable_manager.get_by_key("DATABASE_PASSWORD")

        # Complete database URL by appending the database name or SID
        database_url = f"{database_url_prefix}{self.database_name}"

        engine = create_engine(database_url, connect_args={"password": database_password})
        metadata = MetaData()

        try:
            metadata.reflect(bind=engine)

            table_info = {}
            for table_name, table in metadata.tables.items():
                columns = [(column.name, str(column.type)) for column in table.columns]
                table_info[table_name] = columns

            formatted_str = "Database Schema Information:\n"
            for table, columns in table_info.items():
                formatted_str += f"\nTable: {table}\n"
                for column_name, column_type in columns:
                    formatted_str += f"  Column: {column_name}, Type: {column_type}\n"

            return formatted_str
        except Exception as e:
            error_message = f"Error while listing tables and columns from database: {str(e)}"
            logger.exception(error_message)
            return json.dumps({"error": error_message})
        finally:
            engine.dispose()


if __name__ == "__main__":
    """
    Example usage:
    user_id = "<your Firebase user id>"
    ContextEnvVarsManager.set("user_id", user_id)
    init_firebase_app()
    tool = GetSQLDatabaseMetadata(database_name="your_database")
    print(tool.run())
    """
