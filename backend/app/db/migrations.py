from sqlalchemy import Engine, inspect, text

from app.db.session import is_sqlite_url

SQLITE_COLUMN_MIGRATIONS: dict[str, dict[str, str]] = {
    "predictions": {
        "top_logprobs": "INTEGER",
        "target_num_predict": "INTEGER",
        "target_temperature": "FLOAT",
        "answer_text": "VARCHAR",
    },
    "counterfactual_jobs": {
        "experiment_run_id": "VARCHAR",
    },
    "counterfactuals": {
        "experiment_run_id": "VARCHAR",
    },
    "metrics": {
        "experiment_run_id": "VARCHAR",
    },
}

SQLITE_INDEX_MIGRATIONS = [
    "CREATE INDEX IF NOT EXISTS ix_counterfactual_jobs_experiment_run_id "
    "ON counterfactual_jobs (experiment_run_id)",
    "CREATE INDEX IF NOT EXISTS ix_counterfactuals_experiment_run_id "
    "ON counterfactuals (experiment_run_id)",
    "CREATE INDEX IF NOT EXISTS ix_metrics_experiment_run_id ON metrics (experiment_run_id)",
]


def migrate_sqlite_schema(db_engine: Engine) -> None:
    if not is_sqlite_url(str(db_engine.url)):
        return

    inspector = inspect(db_engine)
    table_names = set(inspector.get_table_names())

    with db_engine.begin() as connection:
        for table_name, columns in SQLITE_COLUMN_MIGRATIONS.items():
            if table_name not in table_names:
                continue

            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_sql in columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(f'ALTER TABLE "{table_name}" ADD COLUMN {column_name} {column_sql}')
                    )

        for index_sql in SQLITE_INDEX_MIGRATIONS:
            connection.execute(text(index_sql))
