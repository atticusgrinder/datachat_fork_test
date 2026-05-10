"""Factory for creating warehouse executors."""

from app.connections.base import WarehouseExecutor
from app.connections.motherduck import MotherDuckExecutor
from app.connections.bigquery import BigQueryExecutor, get_bigquery_access_token
from app.connections.snowflake import SnowflakeExecutor
from app.connections.postgres import PostgreSQLExecutor
from app.connections.redshift import RedshiftExecutor


def create_executor(warehouse_type: str, credentials: dict) -> WarehouseExecutor:
    """Factory function to create the appropriate executor."""
    if warehouse_type == "motherduck":
        return MotherDuckExecutor(
            token=credentials["token"],
            database=credentials.get("database", ""),
        )
    elif warehouse_type == "bigquery":
        return BigQueryExecutor(
            credentials_json=credentials["credentials_json"],
            project_id=credentials["project_id"],
        )
    elif warehouse_type == "snowflake":
        return SnowflakeExecutor(
            account=credentials["account"],
            username=credentials["username"],
            password=credentials["password"],
            warehouse=credentials["warehouse"],
            database=credentials["database"],
        )
    elif warehouse_type == "postgresql":
        return PostgreSQLExecutor(
            host=credentials["host"],
            port=credentials.get("port", "5432"),
            database=credentials["database"],
            username=credentials["username"],
            password=credentials["password"],
        )
    elif warehouse_type == "redshift":
        # Determine auth mode based on provided credentials
        if credentials.get("workgroup"):
            # Serverless mode
            return RedshiftExecutor(
                is_serverless=True,
                workgroup=credentials["workgroup"],
                host=credentials.get("host"),
                database=credentials.get("database", "dev"),
                access_key=credentials["access_key"],
                secret_key=credentials["secret_key"],
                region=credentials.get("region", "us-east-1"),
                port=int(credentials.get("port", "5439")),
            )
        elif credentials.get("cluster_identifier"):
            # IAM auth mode
            return RedshiftExecutor(
                iam=True,
                cluster_identifier=credentials["cluster_identifier"],
                database=credentials.get("database", "dev"),
                db_user=credentials["db_user"],
                access_key=credentials["access_key"],
                secret_key=credentials["secret_key"],
                region=credentials.get("region", "us-east-1"),
            )
        else:
            # Standard auth mode
            return RedshiftExecutor(
                host=credentials["host"],
                port=int(credentials.get("port", "5439")),
                database=credentials.get("database", "dev"),
                username=credentials["username"],
                password=credentials["password"],
            )
    else:
        raise ValueError(f"Unknown warehouse type: {warehouse_type}")
