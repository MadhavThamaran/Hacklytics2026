
# Running Coach (Skeleton)

Two-panel web app:
- Video upload + mock “form score”
- Chatbot + mock response

## BLOCKER

This section describes how to get the app running locally on Windows and common issues.

## Prereqs (Windows)

- Node **20 LTS** (not 22)
- Python **3.11 or 3.12** (not 3.14)

## Run it (use 2 PowerShell windows)

### PowerShell #1 — API (port 8000)

```powershell
cd C:\Users\<YOUR_USER>\Hacklytics2026\apps\api

# create venv with Python 3.12 (or 3.11)
py -3.12 -m venv .venv
# if you only have 3.11: py -3.11 -m venv .venv

.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Test: http://localhost:8000/health → {"ok": true}

PowerShell #2 — Web (port 3000)
powershell
cd C:\Users\<YOUR_USER>\Hacklytics2026\apps\web
npm install
npm run dev
Open: http://localhost:3000

If Next.js fails with “SWC” on Windows
You’re probably on Node 22. Install Node 20, then run:

powershell
cd C:\Users\<YOUR_USER>\Hacklytics2026\apps\web
rm -r -force node_modules
rm -force package-lock.json
rm -r -force .next
npm cache clean --force
npm install
npm run dev

## Databricks setup (optional)

This project optionally integrates with Databricks SQL for metadata storage. Videos and overlay files are **always stored locally** in `apps/api/storage/uploads/`. Databricks stores:
- Job status (`uploads` table)
- Metrics and scores (`video_results` table)

To enable Databricks integration:

1. Create a Databricks Free account and start a SQL Warehouse (Databricks SQL).
2. Generate a Personal Access Token (PAT) from User Settings → Access Tokens.
3. In Databricks SQL, copy the HTTP path for your SQL Warehouse.
4. Create a local `.env` file in the repo root (or set environment variables):

```
DATABRICKS_HOST=https://<your-workspace-host>
DATABRICKS_TOKEN=<your-pat-token>
DATABRICKS_HTTP_PATH=<sql-warehouse-http-path>
```

**Do NOT commit the `.env` file** (it's in `.gitignore`).

5. Run the setup SQL once to create Delta tables. In Databricks SQL editor, run all commands from `databricks/notebooks/setup_tables.sql`.

6. Install API requirements:

```powershell
cd apps/api
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

7. Start the API. When you upload a video:
   - Video is saved locally to `appstructions/api/storage/uploads/{job_id}.mp4`
   - Job metadata is inserted into Databricks `uploads` table
   - Local worker processes the video and writes results locally
   - Metrics and scores are inserted into Databricks `video_results` table

Notes:
- If Databricks env vars are not set, the app works with local storage only (jobs.json).
- If Databricks SQL fails at any point, the app continues with local storage as fallback.
- No secrets are committed; keep `.env` local or set in your deployment environment.