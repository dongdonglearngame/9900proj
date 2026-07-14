from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import Connection, Engine


@dataclass(frozen=True)
class SQLiteMigration:
    version: int
    apply: Callable[[Connection], None]


def _column_names(connection: Connection, table: str) -> set[str]:
    rows = connection.exec_driver_sql(f'PRAGMA table_info("{table}")')
    return {str(row[1]) for row in rows}


def _add_column_if_missing(
    connection: Connection,
    *,
    table: str,
    column: str,
    sql_type: str,
) -> None:
    if column in _column_names(connection, table):
        return
    connection.exec_driver_sql(
        f'ALTER TABLE "{table}" ADD COLUMN "{column}" {sql_type}'
    )


def _upgrade_to_experiment_runs(connection: Connection) -> None:
    prediction_columns = (
        ("top_logprobs", "INTEGER"),
        ("target_num_predict", "INTEGER"),
        ("target_temperature", "FLOAT"),
        ("answer_text", "VARCHAR"),
    )
    for column, sql_type in prediction_columns:
        _add_column_if_missing(
            connection,
            table="predictions",
            column=column,
            sql_type=sql_type,
        )

    experiment_links = (
        "counterfactual_jobs",
        "counterfactuals",
        "metrics",
    )
    for table in experiment_links:
        _add_column_if_missing(
            connection,
            table=table,
            column="experiment_run_id",
            sql_type="VARCHAR",
        )
        connection.exec_driver_sql(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_experiment_run_id "
            f'ON "{table}" (experiment_run_id)'
        )


SQLITE_MIGRATIONS = (SQLiteMigration(version=1, apply=_upgrade_to_experiment_runs),)


def run_sqlite_migrations(database_engine: Engine) -> None:
    """Upgrade existing SQLite databases without deleting persisted demo data."""
    if database_engine.dialect.name != "sqlite":
        return

    with database_engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        applied = {
            int(row[0])
            for row in connection.exec_driver_sql(
                "SELECT version FROM schema_migrations"
            )
        }

        for migration in SQLITE_MIGRATIONS:
            if migration.version in applied:
                continue
            migration.apply(connection)
            connection.exec_driver_sql(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (migration.version,),
            )
