import os
from urllib.parse import urlparse

try:
    from databricks import sql as dbsql
except Exception:
    dbsql = None


def _get_db_config():
    host = os.getenv("DATABRICKS_HOST")
    token = os.getenv("DATABRICKS_TOKEN")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")
    if not host or not token:
        return None
    return {
        "host": host.rstrip("/"),
        "token": token,
        "http_path": http_path,
    }


def _get_sql_connection():
    cfg = _get_db_config()
    if not cfg:
        raise RuntimeError("Databricks config missing in environment")
    if dbsql is None:
        raise RuntimeError("databricks-sql-connector is not installed")

    # server_hostname expects hostname without scheme
    parsed = urlparse(cfg["host"])
    server_hostname = parsed.hostname
    conn = dbsql.connect(server_hostname=server_hostname, http_path=cfg.get("http_path"), access_token=cfg.get("token"))
    return conn


def execute_sql(query: str, params: tuple | None = None) -> None:
    conn = _get_sql_connection()
    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
    finally:
        conn.close()


def fetch_one(query: str, params: tuple | None = None):
    conn = _get_sql_connection()
    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            return cur.fetchone()
    finally:
        conn.close()


def fetch_all(query: str, params: tuple | None = None):
    conn = _get_sql_connection()
    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            return cur.fetchall()
    finally:
        conn.close()
