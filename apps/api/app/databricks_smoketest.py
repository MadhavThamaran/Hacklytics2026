from dotenv import load_dotenv
load_dotenv()

import os
import uuid
from databricks import sql

def env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def connect():
    host = env("DATABRICKS_HOST").replace("https://", "")
    return sql.connect(
        server_hostname=host,
        http_path=env("DATABRICKS_HTTP_PATH"),
        access_token=env("DATABRICKS_TOKEN"),
    )

def main():
    test_id = uuid.uuid4().hex[:8]
    job_id = f"smoke_{test_id}"
    video_path = f"local:smoke/{job_id}.mp4"

    with connect() as conn:
        with conn.cursor() as cur:
            # 1) basic connectivity
            cur.execute("SELECT 1")
            print("SELECT 1 ->", cur.fetchone())

            # 2) ensure tables exist
            cur.execute("SHOW TABLES")
            tables = [r[1] for r in cur.fetchall()]
            print("Tables:", tables)
            if "uploads" not in tables:
                raise RuntimeError("Missing 'uploads' table. Run setup_tables.sql in Databricks SQL.")

            # 3) insert a row
            cur.execute(
                "INSERT INTO uploads (job_id, created_at, video_path, status, rubric_version, overlay_path, error) "
                "VALUES (?, current_timestamp(), ?, 'queued', '0.1.0', NULL, NULL)",
                (job_id, video_path),
            )
            print("Inserted:", job_id)

            # 4) read it back
            cur.execute("SELECT job_id, status, video_path FROM uploads WHERE job_id = ?", (job_id,))
            print("Readback ->", cur.fetchone())

            # 5) update it
            cur.execute("UPDATE uploads SET status='done' WHERE job_id = ?", (job_id,))
            cur.execute("SELECT status FROM uploads WHERE job_id = ?", (job_id,))
            print("Updated status ->", cur.fetchone())

    print("SQL TABULAR SMOKETEST PASSED ✅")

if __name__ == "__main__":
    main()