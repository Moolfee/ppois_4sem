import os


class PostgresConnectionError(RuntimeError):
    pass


class OptionalPostgresProbe:
    def check_connection(self) -> None:
        dsn = os.getenv("GOODS_POSTGRES_DSN", "").strip()
        if not dsn:
            return

        try:
            import psycopg
        except ModuleNotFoundError as error:
            raise PostgresConnectionError(
                
            ) from error

        try:
            with psycopg.connect(dsn, connect_timeout=3):
                return
        except Exception as error:
            raise PostgresConnectionError(
                f"Не удалось подключиться к Postgres: {error}"
            ) from error
