
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