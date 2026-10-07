"""
APCNF Cadre Attendance & Feedback System - Production FastAPI Server
Optimized for Starter Cloud Hosting (1GB RAM, 1 vCPU, 10GB Disk, Always-On)
Supports 1000+ Active Cadres, Persistent SQLite with WAL Mode,
and File-Based Attendance Photo Storage.
"""

import os
import sys
import json
import time
import uuid
import base64
import hmac
import hashlib
import sqlite3
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, Response, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# --- Configuration & Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
PHOTOS_DIR = UPLOADS_DIR / "photos"
DB_PATH = DATA_DIR / "apcnf.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

AUTH_SECRET = os.environ.get("AUTH_SECRET", "APCNF_LOCAL_RBAC_SECRET_2026_KEY").encode("utf-8")
TIMEZONE_OFFSET = datetime.timezone(datetime.timedelta(hours=5, minutes=30))  # IST Asia/Kolkata

# --- Database Helper with WAL Mode ---
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 10000;")
    try:
        yield conn
    finally:
        conn.close()

def get_direct_db():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def init_db():
    conn = get_direct_db()
    cursor = conn.cursor()

    # 1. Cadre Master
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cadres (
        cadre_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        mobile TEXT NOT NULL,
        cadre_type TEXT NOT NULL,
        district TEXT,
        mandal TEXT,
        village TEXT,
        vo TEXT,
        status TEXT DEFAULT 'Active',
        created_at TEXT
    );
    """)

    # 2. Admin Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT DEFAULT 'ADMIN',
        status TEXT DEFAULT 'Active',
        created_at TEXT
    );
    """)

    # 3. Attendance
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        date TEXT,
        time TEXT,
        cadre_id TEXT,
        name TEXT,
        cadre_type TEXT,
        activity TEXT,
        remarks TEXT,
        photo_link TEXT,
        latitude REAL,
        longitude REAL,
        accuracy REAL,
        created_at TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_date ON attendance(date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_cadre ON attendance(cadre_id);")

    # 4. Feedback
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        date TEXT,
        cadre_id TEXT,
        name TEXT,
        cadre_type TEXT,
        training TEXT,
        trainer TEXT,
        content_rating INTEGER,
        trainer_rating INTEGER,
        usefulness_rating INTEGER,
        overall_rating INTEGER,
        suggestions TEXT,
        created_at TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_date ON feedback(date);")

    # Seed Admin User if empty
    cursor.execute("SELECT COUNT(*) as count FROM admin_users")
    if cursor.fetchone()["count"] == 0:
        admin_salt = "apcnf_admin_salt_2026"
        admin_hash = hashlib.sha256(("Admin@APCNF2026" + admin_salt).encode("utf-8")).hexdigest()
        cursor.execute("""
            INSERT INTO admin_users (username, password_hash, salt, name, role, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "admin@apcnf.gov.in",
            admin_hash,
            admin_salt,
            "State Administrator",
            "ADMIN",
            "Active",
            datetime.datetime.now(TIMEZONE_OFFSET).isoformat()
        ))

    # Seed Default Cadres if empty
    cursor.execute("SELECT COUNT(*) as count FROM cadres")
    if cursor.fetchone()["count"] == 0:
        seed_cadres = [
            ("FMT101", "Lakshmi Devi", "9876543210", "FMT", "Anantapur", "Kalyandurg", "Chapiri", "Sri Lakshmi Mahila Sangham", "Active"),
            ("ICRP05", "Ramesh Naidu", "9123456780", "ICRP", "Kurnool", "Adoni", "Arekal", "Navodaya VO", "Active"),
            ("TICRP02", "Saraswathi Bai", "9988776655", "T-ICRP", "Prakasam", "Giddalur", "Mundlapadu", "Chaitanya VO", "Active")
        ]
        now_str = datetime.datetime.now(TIMEZONE_OFFSET).isoformat()
        for c in seed_cadres:
            cursor.execute("""
                INSERT OR IGNORE INTO cadres (cadre_id, name, mobile, cadre_type, district, mandal, village, vo, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (*c, now_str))

    # Seed Initial Attendance if empty
    cursor.execute("SELECT COUNT(*) as count FROM attendance")
    if cursor.fetchone()["count"] == 0:
        yesterday_str = (datetime.datetime.now(TIMEZONE_OFFSET) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        seed_attendance = [
            (
                yesterday_str + "T10:15:00", yesterday_str, "10:15:00",
                "FMT101", "Lakshmi Devi", "FMT", "Attend Meeting",
                "Gram Panchayat monthly review on organic certification & Subhash Palekar methods in Chapiri",
                "https://images.unsplash.com/photo-1595974482597-4b8da8879bc5?auto=format&fit=crop&w=600&q=80",
                14.6820, 77.6010, 5.2, yesterday_str
            ),
            (
                yesterday_str + "T14:40:00", yesterday_str, "14:40:00",
                "ICRP05", "Ramesh Naidu", "ICRP", "Field Visit",
                "PMDS pre-monsoon dry sowing demonstration with 8 farmers in Chapiri cluster",
                "https://images.unsplash.com/photo-1592417817098-8f3d69109853?auto=format&fit=crop&w=600&q=80",
                15.6322, 77.2750, 8.4, yesterday_str
            )
        ]
        for a in seed_attendance:
            cursor.execute("""
                INSERT INTO attendance (timestamp, date, time, cadre_id, name, cadre_type, activity, remarks, photo_link, latitude, longitude, accuracy, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, a)

    # Seed Initial Feedback if empty
    cursor.execute("SELECT COUNT(*) as count FROM feedback")
    if cursor.fetchone()["count"] == 0:
        yesterday_str = (datetime.datetime.now(TIMEZONE_OFFSET) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        seed_feedback = [
            (
                yesterday_str + "T12:00:00", yesterday_str, "FMT101", "Lakshmi Devi", "FMT",
                "PMDS Natural Farming Practices", "Sri Ramana Garu", 5, 5, 5, 5,
                "Very practical session on seed pelleting and Beejamruth preparation.", yesterday_str
            ),
            (
                yesterday_str + "T16:10:00", yesterday_str, "ICRP05", "Ramesh Naidu", "ICRP",
                "Navadhanya Intercropping Models", "Dr. Subba Rao Garu", 5, 4, 5, 5,
                "Need more sample seed kits for demonstrations in drought-prone areas.", yesterday_str
            )
        ]
        for f in seed_feedback:
            cursor.execute("""
                INSERT INTO feedback (timestamp, date, cadre_id, name, cadre_type, training, trainer, content_rating, trainer_rating, usefulness_rating, overall_rating, suggestions, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, f)

    conn.commit()
    conn.close()

init_db()

# --- Token Management (HMAC-SHA256 JWT) ---
def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def base64url_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)

def generate_token(user_id: str, role: str, name: str, extra: Optional[Dict[str, Any]] = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    exp_seconds = 86400 * 30 if role == "CADRE" else 86400  # 30 days for Cadre, 24h for Admin
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role,
        "name": name,
        "iat": now,
        "exp": now + exp_seconds
    }
    if extra:
        payload.update(extra)

    hdr_b64 = base64url_encode(json.dumps(header).encode("utf-8"))
    pay_b64 = base64url_encode(json.dumps(payload).encode("utf-8"))
    signature = hmac.new(AUTH_SECRET, f"{hdr_b64}.{pay_b64}".encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64url_encode(signature)
    return f"{hdr_b64}.{pay_b64}.{sig_b64}"

def verify_token(token: Optional[str], required_role: Optional[str] = None) -> tuple[bool, str, Optional[Dict[str, Any]]]:
    if not token or not isinstance(token, str):
        return False, "Missing token. Authorization required.", None

    parts = token.split(".")
    if len(parts) != 3:
        return False, "Invalid token format.", None

    expected_sig = base64url_encode(
        hmac.new(AUTH_SECRET, f"{parts[0]}.{parts[1]}".encode("utf-8"), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(parts[2], expected_sig):
        return False, "Invalid token signature. Access denied.", None

    try:
        payload = json.loads(base64url_decode(parts[1]).decode("utf-8"))
    except Exception:
        return False, "Corrupted token payload.", None

    if payload.get("exp", 0) < int(time.time()):
        return False, "Session token has expired. Please log in again.", None

    if required_role and payload.get("role") != required_role:
        return False, f"Access denied. Required role: {required_role}", None

    return True, "", payload

# --- Photo Disk Storage Helper ---
def save_photo_to_disk(base64_data: str, cadre_id: str) -> str:
    if not base64_data or not base64_data.strip():
        return ""

    if base64_data.startswith("http://") or base64_data.startswith("https://"):
        return base64_data

    clean_b64 = base64_data
    if "base64," in clean_b64:
        clean_b64 = clean_b64.split("base64,")[1]

    try:
        img_bytes = base64.b64decode(clean_b64)
    except Exception:
        return ""

    now_tag = datetime.datetime.now(TIMEZONE_OFFSET).strftime("%Y%m%d_%H%M%S")
    rand_str = uuid.uuid4().hex[:6]
    file_name = f"{cadre_id}_{now_tag}_{rand_str}.jpg"
    file_path = PHOTOS_DIR / file_name

    with open(file_path, "wb") as f:
        f.write(img_bytes)

    return f"/uploads/photos/{file_name}"

# --- CSV Generation Helper ---
def generate_attendance_csv(records: List[Dict[str, Any]]) -> str:
    headers = [
        "Date", "Time", "Cadre ID", "Cadre Name", "Cadre Type",
        "Activity", "Remarks", "Latitude", "Longitude", "Accuracy (m)", "Photo URL"
    ]
    def escape_csv(val):
        if val is None:
            return '""'
        s = str(val).replace('"', '""')
        return f'"{s}"'

    lines = [",".join(escape_csv(h) for h in headers)]
    for r in records:
        row = [
            r.get("date", ""),
            r.get("time", ""),
            r.get("cadreId", ""),
            r.get("name", ""),
            r.get("cadreType", ""),
            r.get("activity", ""),
            r.get("remarks", ""),
            r.get("latitude", ""),
            r.get("longitude", ""),
            r.get("accuracy", ""),
            r.get("photoLink", "")
        ]
        lines.append(",".join(escape_csv(val) for val in row))
    return "\r\n".join(lines)

# --- FastAPI App Setup ---
app = FastAPI(
    title="APCNF Cadre Attendance & Feedback Server",
    version="2.2.0-Starter",
    description="High-performance backend for APCNF Cadre reporting and Admin oversight."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

@app.get("/", response_class=HTMLResponse)
def get_root():
    index_file = BASE_DIR / "Index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h2>APCNF Cadre Portal is Online</h2>")

# --- Core Action Processing Logic (Shared by /exec and REST endpoints) ---
def process_action(payload: Dict[str, Any]):
    action = payload.get("action", "")
    conn = get_direct_db()
    cursor = conn.cursor()

    try:
        # 1. Cadre Login
        if action == "login":
            cadre_id = str(payload.get("cadreId", "")).strip().upper()
            mobile = str(payload.get("mobile", "")).strip()[-10:]

            cursor.execute("""
                SELECT cadre_id, name, mobile, cadre_type, district, mandal, village, vo, status
                FROM cadres
                WHERE UPPER(cadre_id) = ? AND SUBSTR(mobile, -10) = ?
            """, (cadre_id, mobile))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "message": "Cadre not found. Verify Cadre ID and Mobile Number."}

            cadre_dict = {
                "cadreId": row["cadre_id"],
                "name": row["name"],
                "mobile": row["mobile"],
                "cadreType": row["cadre_type"],
                "district": row["district"],
                "mandal": row["mandal"],
                "village": row["village"],
                "vo": row["vo"],
                "status": row["status"]
            }

            if cadre_dict["status"].lower() != "active":
                return {"success": False, "message": "Cadre status is inactive. Contact Mandal Incharge."}

            token = generate_token(cadre_dict["cadreId"], "CADRE", cadre_dict["name"], {
                "mobile": cadre_dict["mobile"],
                "cadreType": cadre_dict["cadreType"]
            })

            return {
                "success": True,
                "role": "CADRE",
                "token": token,
                "cadre": cadre_dict,
                "message": "Cadre authentication successful."
            }

        # 2. Admin Login
        if action == "adminLogin":
            username = str(payload.get("username", "")).strip().lower()
            password = str(payload.get("password", ""))

            cursor.execute("""
                SELECT username, password_hash, salt, name, role, status
                FROM admin_users
                WHERE LOWER(username) = ? AND status = 'Active'
            """, (username,))
            admin_row = cursor.fetchone()

            if admin_row:
                computed_hash = hashlib.sha256((password + admin_row["salt"]).encode("utf-8")).hexdigest()
                if computed_hash == admin_row["password_hash"]:
                    token = generate_token(admin_row["username"], "ADMIN", admin_row["name"])
                    return {
                        "success": True,
                        "role": "ADMIN",
                        "token": token,
                        "admin": {
                            "username": admin_row["username"],
                            "name": admin_row["name"],
                            "role": "ADMIN"
                        },
                        "message": "Admin authentication successful."
                    }

            return {"success": False, "message": "Invalid admin credentials."}

        # 3. Save Attendance (Strict Token Auth & Identity Binding)
        if action == "saveAttendance":
            valid, err, auth = verify_token(payload.get("token"), "CADRE")
            if not valid:
                return JSONResponse(status_code=403, content={"success": False, "error": "UNAUTHORIZED", "message": err or "Authentication token required."})

            auth_cadre_id = str(auth.get("sub", "")).strip().upper()
            if payload.get("cadreId"):
                client_cadre_id = str(payload.get("cadreId", "")).strip().upper()
                if client_cadre_id != auth_cadre_id:
                    return JSONResponse(status_code=403, content={"success": False, "error": "UNAUTHORIZED", "message": "Token identity mismatch. Client cadreId does not match authenticated user."})

            cursor.execute("""
                SELECT cadre_id, name, mobile, cadre_type, status
                FROM cadres
                WHERE UPPER(cadre_id) = ?
            """, (auth_cadre_id,))
            cadre_row = cursor.fetchone()
            if not cadre_row or str(cadre_row["status"]).lower() != "active":
                return JSONResponse(status_code=403, content={"success": False, "error": "UNAUTHORIZED", "message": "Authenticated cadre is not active or not found."})

            cadre_id = cadre_row["cadre_id"]
            name = cadre_row["name"]
            mobile = cadre_row["mobile"]
            cadre_type = cadre_row["cadre_type"]

            activity = str(payload.get("activity", "Field Visit"))
            now_dt = datetime.datetime.now(TIMEZONE_OFFSET)
            today_str = now_dt.strftime("%Y-%m-%d")
            time_str = now_dt.strftime("%H:%M:%S")

            raw_photo = payload.get("photoBase64", "")
            photo_url = save_photo_to_disk(raw_photo, cadre_id)

            cursor.execute("""
                INSERT INTO attendance (timestamp, date, time, cadre_id, name, cadre_type, activity, remarks, photo_link, latitude, longitude, accuracy, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now_dt.isoformat(),
                today_str,
                time_str,
                cadre_id,
                name,
                cadre_type,
                activity,
                payload.get("remarks", ""),
                photo_url,
                float(payload.get("latitude") or 0.0),
                float(payload.get("longitude") or 0.0),
                float(payload.get("accuracy") or 0.0),
                today_str
            ))
            conn.commit()
            return {
                "success": True,
                "message": f"Attendance for '{activity}' recorded successfully."
            }

        # 4. Save Feedback (Strict Token Auth & Identity Binding)
        if action == "saveFeedback":
            valid, err, auth = verify_token(payload.get("token"), "CADRE")
            if not valid:
                return JSONResponse(status_code=403, content={"success": False, "error": "UNAUTHORIZED", "message": err or "Authentication token required."})

            auth_cadre_id = str(auth.get("sub", "")).strip().upper()
            if payload.get("cadreId"):
                client_cadre_id = str(payload.get("cadreId", "")).strip().upper()
                if client_cadre_id != auth_cadre_id:
                    return JSONResponse(status_code=403, content={"success": False, "error": "UNAUTHORIZED", "message": "Token identity mismatch. Client cadreId does not match authenticated user."})

            cursor.execute("""
                SELECT cadre_id, name, mobile, cadre_type, status
                FROM cadres
                WHERE UPPER(cadre_id) = ?
            """, (auth_cadre_id,))
            cadre_row = cursor.fetchone()
            if not cadre_row or str(cadre_row["status"]).lower() != "active":
                return JSONResponse(status_code=403, content={"success": False, "error": "UNAUTHORIZED", "message": "Authenticated cadre is not active or not found."})

            cadre_id = cadre_row["cadre_id"]
            name = cadre_row["name"]
            mobile = cadre_row["mobile"]
            cadre_type = cadre_row["cadre_type"]

            now_dt = datetime.datetime.now(TIMEZONE_OFFSET)
            today_str = now_dt.strftime("%Y-%m-%d")

            cursor.execute("""
                INSERT INTO feedback (timestamp, date, cadre_id, name, cadre_type, training, trainer, content_rating, trainer_rating, usefulness_rating, overall_rating, suggestions, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now_dt.isoformat(),
                today_str,
                cadre_id,
                name,
                cadre_type,
                payload.get("training", "Training Session"),
                payload.get("trainer", "Resource Person"),
                int(payload.get("contentRating") or 5),
                int(payload.get("trainerRating") or 5),
                int(payload.get("usefulnessRating") or 5),
                int(payload.get("overallRating") or 5),
                payload.get("suggestions", ""),
                today_str
            ))
            conn.commit()
            return {"success": True, "message": "Feedback submitted successfully."}

        # 5. Cadre Dashboard (Strict Token Auth & Identity Binding)
        if action == "getDashboard":
            valid, err, auth = verify_token(payload.get("token"), "CADRE")
            if not valid:
                return JSONResponse(status_code=403, content={"success": False, "error": "UNAUTHORIZED", "message": err or "Authentication token required."})

            auth_cadre_id = str(auth.get("sub", "")).strip().upper()
            if payload.get("cadreId"):
                client_cadre_id = str(payload.get("cadreId", "")).strip().upper()
                if client_cadre_id != auth_cadre_id:
                    return JSONResponse(status_code=403, content={"success": False, "error": "UNAUTHORIZED", "message": "Token identity mismatch. Client cadreId does not match authenticated user."})

            today_str = datetime.datetime.now(TIMEZONE_OFFSET).strftime("%Y-%m-%d")

            cursor.execute("SELECT COUNT(*) as c FROM attendance WHERE activity = 'Field Visit'")
            total_field = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM attendance WHERE activity = 'Attend Meeting'")
            total_meet = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM feedback")
            total_fb = cursor.fetchone()["c"]

            cursor.execute("SELECT id FROM attendance WHERE UPPER(cadre_id) = ? AND date = ? AND activity = 'Field Visit'", (auth_cadre_id, today_str))
            fv_done = cursor.fetchone() is not None

            cursor.execute("SELECT id FROM attendance WHERE UPPER(cadre_id) = ? AND date = ? AND activity = 'Attend Meeting'", (auth_cadre_id, today_str))
            mt_done = cursor.fetchone() is not None

            return {
                "success": True,
                "data": {
                    "today": today_str,
                    "totalFieldVisits": total_field,
                    "totalMeetings": total_meet,
                    "totalFeedback": total_fb,
                    "myAttendance": {
                        "fieldVisitDone": fv_done,
                        "meetingDone": mt_done
                    }
                }
            }

        # 6. Admin Endpoints (Strict Verification)
        admin_actions = ["getAdminDashboard", "getAdminAllData", "getAdminAttendanceList", "getAdminFeedbackList", "getAdminCadreList", "exportAdminAttendance"]
        if action in admin_actions:
            valid, err, _ = verify_token(payload.get("token"), "ADMIN")
            if not valid:
                return JSONResponse(status_code=403, content={"success": False, "error": "UNAUTHORIZED", "message": err})

            today_str = datetime.datetime.now(TIMEZONE_OFFSET).strftime("%Y-%m-%d")

            if action == "getAdminDashboard":
                cursor.execute("SELECT COUNT(*) as c FROM cadres")
                total_cadres = cursor.fetchone()["c"]

                cursor.execute("SELECT COUNT(*) as c FROM cadres WHERE status = 'Active'")
                active_cadres = cursor.fetchone()["c"]

                cursor.execute("SELECT COUNT(*) as c FROM attendance WHERE date = ? AND activity = 'Field Visit'", (today_str,))
                today_fv = cursor.fetchone()["c"]

                cursor.execute("SELECT COUNT(*) as c FROM attendance WHERE date = ? AND activity = 'Attend Meeting'", (today_str,))
                today_mt = cursor.fetchone()["c"]

                cursor.execute("SELECT COUNT(*) as c, AVG(overall_rating) as avg_r FROM feedback")
                fb_row = cursor.fetchone()
                total_fb = fb_row["c"] or 0
                avg_rating = round(fb_row["avg_r"] or 5.0, 1)

                cursor.execute("""
                    SELECT date, time, cadre_id as cadreId, name, cadre_type as cadreType,
                           activity, remarks, photo_link as photoLink, latitude, longitude
                    FROM attendance
                    ORDER BY id DESC LIMIT 5
                """)
                recent = [dict(r) for r in cursor.fetchall()]

                return {
                    "success": True,
                    "data": {
                        "today": today_str,
                        "totalCadres": total_cadres,
                        "activeCadres": active_cadres,
                        "todayFieldVisits": today_fv,
                        "todayMeetings": today_mt,
                        "totalFeedback": total_fb,
                        "averageRating": avg_rating,
                        "recentAttendance": recent
                    }
                }

            if action == "getAdminAllData":
                cursor.execute("SELECT * FROM cadres")
                cadres_list = [dict(r) for r in cursor.fetchall()]
                cursor.execute("SELECT COUNT(*) as c FROM attendance")
                tot_att = cursor.fetchone()["c"]
                cursor.execute("SELECT COUNT(*) as c FROM feedback")
                tot_fb = cursor.fetchone()["c"]

                return {
                    "success": True,
                    "data": {
                        "cadres": cadres_list,
                        "totalAttendanceRecords": tot_att,
                        "totalFeedbackRecords": tot_fb
                    }
                }

            if action == "getAdminAttendanceList":
                f_date = payload.get("date")
                f_from = payload.get("fromDate")
                f_to = payload.get("toDate")
                f_act = payload.get("activity")
                f_type = payload.get("cadreType")
                f_q = (payload.get("query") or "").strip().lower()

                query = "SELECT date, time, cadre_id as cadreId, name, cadre_type as cadreType, activity, remarks, photo_link as photoLink, latitude, longitude, accuracy FROM attendance WHERE 1=1"
                params = []

                if f_date and f_date != "ALL":
                    query += " AND date = ?"
                    params.append(f_date)
                if f_from:
                    query += " AND date >= ?"
                    params.append(f_from)
                if f_to:
                    query += " AND date <= ?"
                    params.append(f_to)
                if f_act and f_act != "ALL":
                    query += " AND LOWER(activity) = LOWER(?)"
                    params.append(f_act)
                if f_type and f_type != "ALL":
                    query += " AND UPPER(cadre_type) = UPPER(?)"
                    params.append(f_type)
                if f_q:
                    query += " AND (LOWER(cadre_id) LIKE ? OR LOWER(name) LIKE ? OR LOWER(remarks) LIKE ?)"
                    params.extend([f"%{f_q}%", f"%{f_q}%", f"%{f_q}%"])

                query += " ORDER BY id DESC LIMIT 200"
                cursor.execute(query, params)
                records = [dict(r) for r in cursor.fetchall()]
                return {"success": True, "count": len(records), "data": records}

            if action == "getAdminFeedbackList":
                f_type = payload.get("cadreType")
                f_rating = payload.get("minRating")
                f_q = (payload.get("query") or "").strip().lower()

                query = "SELECT date, cadre_id as cadreId, name, cadre_type as cadreType, training, trainer, content_rating as contentRating, trainer_rating as trainerRating, usefulness_rating as usefulnessRating, overall_rating as overallRating, suggestions FROM feedback WHERE 1=1"
                params = []

                if f_type and f_type != "ALL":
                    query += " AND UPPER(cadre_type) = UPPER(?)"
                    params.append(f_type)
                if f_rating and str(f_rating) != "ALL":
                    query += " AND overall_rating >= ?"
                    params.append(int(f_rating))
                if f_q:
                    query += " AND (LOWER(cadre_id) LIKE ? OR LOWER(name) LIKE ? OR LOWER(training) LIKE ? OR LOWER(trainer) LIKE ? OR LOWER(suggestions) LIKE ?)"
                    params.extend([f"%{f_q}%", f"%{f_q}%", f"%{f_q}%", f"%{f_q}%", f"%{f_q}%"])

                query += " ORDER BY id DESC LIMIT 200"
                cursor.execute(query, params)
                records = [dict(r) for r in cursor.fetchall()]
                return {"success": True, "count": len(records), "data": records}

            if action == "getAdminCadreList":
                f_type = payload.get("cadreType")
                f_status = payload.get("status")
                f_q = (payload.get("query") or "").strip().lower()

                query = "SELECT cadre_id as cadreId, name, mobile, cadre_type as cadreType, district, mandal, village, vo, status FROM cadres WHERE 1=1"
                params = []

                if f_type and f_type != "ALL":
                    query += " AND UPPER(cadre_type) = UPPER(?)"
                    params.append(f_type)
                if f_status and f_status != "ALL":
                    query += " AND LOWER(status) = LOWER(?)"
                    params.append(f_status)
                if f_q:
                    query += " AND (LOWER(cadre_id) LIKE ? OR LOWER(name) LIKE ? OR mobile LIKE ? OR LOWER(district) LIKE ? OR LOWER(mandal) LIKE ? OR LOWER(village) LIKE ?)"
                    params.extend([f"%{f_q}%", f"%{f_q}%", f"%{f_q}%", f"%{f_q}%", f"%{f_q}%"])

                cursor.execute(query, params)
                cadres_res = [dict(r) for r in cursor.fetchall()]
                return {"success": True, "count": len(cadres_res), "data": cadres_res}

            if action == "exportAdminAttendance":
                from_date = payload.get("fromDate") or "2000-01-01"
                to_date = payload.get("toDate") or "2099-12-31"
                f_act = payload.get("activity")
                f_type = payload.get("cadreType")

                query = "SELECT date, time, cadre_id as cadreId, name, cadre_type as cadreType, activity, remarks, latitude, longitude, accuracy, photo_link as photoLink FROM attendance WHERE date >= ? AND date <= ?"
                params = [from_date, to_date]

                if f_act and f_act != "ALL":
                    query += " AND LOWER(activity) = LOWER(?)"
                    params.append(f_act)
                if f_type and f_type != "ALL":
                    query += " AND UPPER(cadre_type) = UPPER(?)"
                    params.append(f_type)

                query += " ORDER BY date DESC, time DESC"
                cursor.execute(query, params)
                records = [dict(r) for r in cursor.fetchall()]

                csv_text = generate_attendance_csv(records)
                filename = f"APCNF_Attendance_{from_date}_to_{to_date}.csv"

                return {
                    "success": True,
                    "filename": filename,
                    "fromDate": from_date,
                    "toDate": to_date,
                    "count": len(records),
                    "csvContent": csv_text,
                    "data": records
                }

        return {"success": False, "message": f"Invalid action parameter: {action}"}

    finally:
        conn.close()

# --- Universal /exec Endpoint (Used by Android App & Web Apps Script API) ---
@app.get("/exec")
def exec_get(action: Optional[str] = None, token: Optional[str] = None, fromDate: Optional[str] = None, toDate: Optional[str] = None):
    now_ist = datetime.datetime.now(TIMEZONE_OFFSET).strftime("%Y-%m-%d %H:%M:%S")

    if action == "status" or not action:
        return {
            "status": "online",
            "appName": "APCNF Cadre Attendance & Feedback",
            "version": "2.2.0-Starter",
            "serverTime": now_ist
        }

    if action == "downloadAttendanceCsv":
        valid, err, _ = verify_token(token, "ADMIN")
        if not valid:
            return JSONResponse(status_code=403, content={"success": False, "error": "UNAUTHORIZED", "message": err})

        conn = get_direct_db()
        cursor = conn.cursor()
        f_from = fromDate or "2000-01-01"
        f_to = toDate or "2099-12-31"

        cursor.execute("""
            SELECT date, time, cadre_id as cadreId, name, cadre_type as cadreType,
                   activity, remarks, latitude, longitude, accuracy, photo_link as photoLink
            FROM attendance
            WHERE date >= ? AND date <= ?
            ORDER BY date DESC, time DESC
        """, (f_from, f_to))
        records = [dict(row) for row in cursor.fetchall()]
        conn.close()

        csv_text = generate_attendance_csv(records)
        filename = f"APCNF_Attendance_{f_from}_to_{f_to}.csv"
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    return {"success": False, "message": f"Unsupported GET action: {action}"}

@app.post("/exec")
async def exec_post(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return process_action(payload)

# --- Direct REST Endpoints for compatibility ---
@app.get("/api/cadre")
def api_get_cadre(id: str = Query(...), mobile: str = Query(...)):
    conn = get_direct_db()
    cursor = conn.cursor()
    clean_id = id.strip().upper()
    clean_mob = mobile.strip()[-10:]
    cursor.execute("""
        SELECT cadre_id as cadreId, name, mobile, cadre_type as cadreType, district, mandal, village, vo, status
        FROM cadres WHERE UPPER(cadre_id) = ? AND SUBSTR(mobile, -10) = ?
    """, (clean_id, clean_mob))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"success": True, "cadre": dict(row)}
    return JSONResponse(status_code=404, content={"success": False, "message": "Cadre not found."})

@app.post("/api/attendance")
async def api_post_attendance(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    payload["action"] = "saveAttendance"
    return process_action(payload)

@app.post("/api/feedback")
async def api_post_feedback(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    payload["action"] = "saveFeedback"
    return process_action(payload)

@app.get("/api/dashboard")
def api_get_dashboard(cadreId: str = Query(...), token: Optional[str] = Query(None)):
    payload = {"action": "getDashboard", "cadreId": cadreId, "token": token}
    return process_action(payload)

@app.get("/api/export/attendance")
def api_export_csv(token: str = Query(...), fromDate: Optional[str] = None, toDate: Optional[str] = None):
    return exec_get(action="downloadAttendanceCsv", token=token, fromDate=fromDate, toDate=toDate)

# --- Bulk Cadre Importer Helper (For importing 1,000 cadres) ---
@app.post("/api/cadres/bulk-import")
async def bulk_import_cadres(request: Request):
    payload = await request.json()
    items = payload.get("cadres", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return {"success": False, "message": "Expected a list of cadre objects."}

    conn = get_direct_db()
    cursor = conn.cursor()
    inserted = 0
    now_str = datetime.datetime.now(TIMEZONE_OFFSET).isoformat()

    for item in items:
        cid = str(item.get("cadreId", "")).strip().upper()
        name = str(item.get("name", "")).strip()
        mob = str(item.get("mobile", "")).strip()
        ctype = str(item.get("cadreType", "FMT")).strip()
        dist = item.get("district", "")
        mandal = item.get("mandal", "")
        vill = item.get("village", "")
        vo = item.get("vo", "")
        stat = item.get("status", "Active")

        if cid and name and mob:
            cursor.execute("""
                INSERT OR REPLACE INTO cadres (cadre_id, name, mobile, cadre_type, district, mandal, village, vo, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cid, name, mob, ctype, dist, mandal, vill, vo, stat, now_str))
            inserted += 1

    conn.commit()
    conn.close()
    return {"success": True, "importedCount": inserted, "message": f"Successfully imported {inserted} cadres."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting APCNF FastAPI Production Server on http://0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
