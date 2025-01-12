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
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.repositories.agent_flow_spec_storage import AgentFlowSpecStorage
from backend.repositories.user_variable_storage import UserVariableStorage
from backend.services.user_variable_manager import UserVariableManager

logger = logging.getLogger(__name__)


class SelectFromSQLDatabase(BaseTool):
    """Select rows from a SQL database using SQLAlchemy."""

    database_name: str = Field(..., description="Database name (for PostgreSQL, MySQL) or SID (for Oracle).")
    table: str = Field(..., description="Table name to select from.")
    columns: list[str] = Field(..., description="Columns to select, e.g. ['id', 'name', 'email'].")
    filters: dict = Field(default={}, description="Filters to apply to the query, e.g. {'name': 'Alice'}.")
    order_by: str = Field(default="", description="Column to order the results by.")
    order_direction: str = Field(default="ASC", description="Order direction (ASC or DESC).")
    limit: int = Field(default=100, description="Maximum number of rows to return.")

    def run(self) -> str:
        """Execute the SQL query and return the result as a JSON string."""
        user_variable_manager = UserVariableManager(UserVariableStorage(), AgentFlowSpecStorage())
        database_url_prefix = user_variable_manager.get_by_key("DATABASE_URL_PREFIX")
        database_password = user_variable_manager.get_by_key("DATABASE_PASSWORD")

        # Complete database URL by appending the database name or SID
        database_url = f"{database_url_prefix}{self.database_name}"

        engine = create_engine(database_url, connect_args={"password": database_password})
        Session = sessionmaker(bind=engine)

        # Construct the raw SQL query dynamically
        columns = "*" if "*" in self.columns else ", ".join(self.columns)
        sql_query = f"SELECT {columns} FROM {self.table}"

        # Applying filters
        if self.filters:
            filter_clauses = " AND ".join([f"{col} = :{col}" for col in self.filters])
            sql_query += f" WHERE {filter_clauses}"

        # Adding ordering
        if self.order_by:
            sql_query += f" ORDER BY {self.order_by} {self.order_direction}"

        # Limiting results
        sql_query += f" LIMIT {self.limit}"

        try:
            with Session() as session:
                result = session.execute(text(sql_query), params=self.filters)
                rows = [row._asdict() for row in result]
            return json.dumps(rows, indent=4, default=str)
        except Exception as e:
            logger.exception(f"Error while selecting from database: {e}")
            return json.dumps({"error": "An error occurred while processing the request"})
        finally:
            engine.dispose()


if __name__ == "__main__":
    """
    Example usage:
    user_id = "<your Firebase user id>"
    ContextEnvVarsManager.set("user_id", user_id)
    init_firebase_app()
    tool = SelectFromSQLDatabase(
        database_name="your_database",
        table="users",
        columns=["id", "name", "email"],
        filters={"name": "Alice"},
        order_by="id",
        order_direction="ASC",
        limit=10,
    )
    print(tool.run())
    """
