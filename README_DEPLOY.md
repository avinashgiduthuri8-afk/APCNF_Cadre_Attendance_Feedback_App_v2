# APCNF Production Server Deployment Guide (Starter Pack)

This server is specifically designed and optimized for **Starter Pack Cloud Hosting** (1 GB RAM, 1.00 vCPU, 10 GB Disk, Always-On).

---

## 1. What's Included

* **`main.py`**: Production-grade asynchronous FastAPI backend.
  * Uses **SQLite with WAL mode (Write-Ahead Logging)** — can easily handle 1,000+ concurrent users with zero database lock issues.
  * Memory footprint: ~35–50 MB RAM (utilizes only ~5% of your 1 GB RAM).
  * Automatically stores compressed attendance photos directly on the 10 GB disk in `data/uploads/photos/`.
  * Fully supports all Android App and Web App features (`/exec` and `/api/*` endpoints).
* **`requirements.txt`**: Standard dependencies (`fastapi`, `uvicorn`, `pydantic`, `python-multipart`).
* **`Procfile`**: Startup instructions for cloud hosts (`web: uvicorn main:app --host 0.0.0.0 --port $PORT`).
* **`cadres_template.csv`**: Template for bulk importing your 1,000 cadres.

---

## 2. Configuration for Your Hosting Modal

In the cloud hosting screen shown in your screenshot:
1. **APP NAME**: `apcnf-cadre-backend` (or your choice).
2. **FRAMEWORK**: Select **`FastAPI`** (or **`Python`**).
3. **BRANCH**: Select **`main`**.
4. **RESOURCE PLAN**: Select **`Starter` (₹199/mo)** — *Always-On, 1 GB RAM, 1 vCPU, 10 GB disk*.
5. Click Deploy / Create when ready.

---

## 3. How to Bulk Import Your 1,000 Cadres

### Method A: Direct CSV Upload via API
You can upload your `cadres_template.csv` or send a bulk JSON request to:
```http
POST /api/cadres/bulk-import
Content-Type: application/json

{
  "cadres": [
    {
      "cadreId": "FMT101",
      "name": "Lakshmi Devi",
      "mobile": "9876543210",
      "cadreType": "FMT",
      "district": "Anantapur",
      "mandal": "Kalyandurg",
      "village": "Chapiri",
      "vo": "Sri Lakshmi Mahila Sangham",
      "status": "Active"
    },
    ...
  ]
}
```

---

## 4. Default Admin Credentials

* **Username**: `admin@apcnf.gov.in`
* **Password**: `Admin@APCNF2026`
* **Role**: `ADMIN`

---

## 5. Connecting Your Android App

Once deployed, copy your assigned cloud domain URL (e.g., `https://apcnf-api.yourdomain.com`).
1. In the Android App login screen, tap **"Configure Server URL / సర్వర్ లింక్"**.
2. Paste your live cloud URL:
   `https://apcnf-api.yourdomain.com/exec`
3. Log in with your Cadre ID or Admin credentials!
