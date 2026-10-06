#!/usr/bin/env python3
"""
Localhost Mock Server for APCNF Cadre Attendance & Feedback App v2
Supports Role-Based Access Control (RBAC): CADRE & ADMIN roles.
Serves the web client and simulates both Google Apps Script Web App
and the REST API endpoint (doPost) for Android and Web clients.
"""

import http.server
import socketserver
import json
import urllib.parse
import os
import datetime
import hashlib
import hmac
import base64
import time

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
AUTH_SECRET = b"APCNF_LOCAL_RBAC_SECRET_2026_KEY"

# Sample Master Cadre Data
CADRE_MASTER = [
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
    {
        "cadreId": "ICRP05",
        "name": "Ramesh Naidu",
        "mobile": "9123456780",
        "cadreType": "ICRP",
        "district": "Kurnool",
        "mandal": "Adoni",
        "village": "Arekal",
        "vo": "Navodaya VO",
        "status": "Active"
    },
    {
        "cadreId": "TICRP02",
        "name": "Saraswathi Bai",
        "mobile": "9988776655",
        "cadreType": "T-ICRP",
        "district": "Prakasam",
        "mandal": "Giddalur",
        "village": "Mundlapadu",
        "vo": "Chaitanya VO",
        "status": "Active"
    }
]

# Admin Users (password: Admin@APCNF2026)
ADMIN_SALT = "apcnf_admin_salt_2026"
ADMIN_PASSWORD_HASH = hashlib.sha256(("Admin@APCNF2026" + ADMIN_SALT).encode("utf-8")).hexdigest()

ADMIN_USERS = [
    {
        "username": "admin@apcnf.gov.in",
        "passwordHash": ADMIN_PASSWORD_HASH,
        "salt": ADMIN_SALT,
        "name": "State Administrator",
        "role": "ADMIN",
        "status": "Active"
    }
]

# In-memory storage for test submissions
ATTENDANCE_DB = []
FEEDBACK_DB = []

def generate_token(user_id, role, name):
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8")).decode("utf-8").rstrip("=")
    exp = int(time.time()) + (86400 if role == "ADMIN" else 2592000)
    payload_data = {
        "sub": user_id,
        "role": role,
        "name": name,
        "exp": exp,
        "iat": int(time.time())
    }
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode("utf-8")).decode("utf-8").rstrip("=")
    signing_input = f"{header}.{payload}".encode("utf-8")
    sig = base64.urlsafe_b64encode(hmac.new(AUTH_SECRET, signing_input, hashlib.sha256).digest()).decode("utf-8").rstrip("=")
    return f"{header}.{payload}.{sig}"

def verify_token(token, required_role=None):
    if not token or not isinstance(token, str):
        return False, "Missing authentication token.", None
    parts = token.split(".")
    if len(parts) != 3:
        return False, "Invalid token format.", None
    header, payload, sig = parts
    signing_input = f"{header}.{payload}".encode("utf-8")
    expected_sig = base64.urlsafe_b64encode(hmac.new(AUTH_SECRET, signing_input, hashlib.sha256).digest()).decode("utf-8").rstrip("=")
    if not hmac.compare_digest(sig, expected_sig):
        return False, "Invalid token signature.", None
    try:
        padded_payload = payload + "=" * (-len(payload) % 4)
        payload_data = json.loads(base64.urlsafe_b64decode(padded_payload.encode("utf-8")).decode("utf-8"))
    except Exception:
        return False, "Invalid token payload.", None

    if payload_data.get("exp", 0) < int(time.time()):
        return False, "Token has expired.", None

    if required_role and payload_data.get("role") != required_role:
        return False, f"Access denied. Required role: {required_role}, user role: {payload_data.get('role')}", None

    return True, None, payload_data

class LocalDevHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path
        query = urllib.parse.parse_qs(url_parts.query)

        # Serve Web App at root
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(os.path.join(DIRECTORY, "Index.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # Mock API: Fetch Cadre
        if path == "/api/cadre":
            cid = query.get("id", [""])[0].strip().upper()
            mob = query.get("mobile", [""])[0].strip()[-10:]
            matched = next((c for c in CADRE_MASTER if c["cadreId"].upper() == cid and c["mobile"][-10:] == mob), None)
            if matched:
                token = generate_token(matched["cadreId"], "CADRE", matched["name"])
                self.send_json_response({"success": True, "role": "CADRE", "token": token, "cadre": matched})
            else:
                self.send_json_response({"success": False, "message": "Cadre not found."})
            return

        # Mock API: Cadre Dashboard
        if path == "/api/dashboard":
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            cid = query.get("cadreId", [""])[0].strip().upper()
            my_field = any(a.get("cadreId", "").upper() == cid and a.get("activity") == "Field Visit" for a in ATTENDANCE_DB)
            my_meet = any(a.get("cadreId", "").upper() == cid and a.get("activity") == "Attend Meeting" for a in ATTENDANCE_DB)
            field_count = len([a for a in ATTENDANCE_DB if a.get("activity") == "Field Visit"]) + 8
            meet_count = len([a for a in ATTENDANCE_DB if a.get("activity") == "Attend Meeting"]) + 4

            self.send_json_response({
                "today": today,
                "totalFieldVisits": field_count,
                "totalMeetings": meet_count,
                "totalFeedback": len(FEEDBACK_DB) + 15,
                "myAttendance": {
                    "fieldVisitDone": my_field,
                    "meetingDone": my_meet
                }
            })
            return

        super().do_GET()

    def do_POST(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        # REST API endpoint matching Google Apps Script doPost (/exec or /api/post)
        if path == "/exec" or path == "/api/post":
            action = payload.get("action")

            # 1. Cadre Login
            if action == "login":
                cid = payload.get("cadreId", "").strip().upper()
                mob = payload.get("mobile", "").strip()[-10:]
                matched = next((c for c in CADRE_MASTER if c["cadreId"].upper() == cid and c["mobile"][-10:] == mob), None)
                if matched:
                    token = generate_token(matched["cadreId"], "CADRE", matched["name"])
                    self.send_json_response({
                        "success": True,
                        "role": "CADRE",
                        "token": token,
                        "message": "Cadre authentication successful.",
                        "cadre": matched
                    })
                else:
                    self.send_json_response({"success": False, "message": "Cadre not found. Check Cadre ID and Mobile."})
                return

            # 2. Admin Login
            if action == "adminLogin":
                username = payload.get("username", "").strip().lower()
                password = payload.get("password", "")
                admin_user = next((u for u in ADMIN_USERS if u["username"].lower() == username and u["status"] == "Active"), None)
                if admin_user:
                    computed_hash = hashlib.sha256((password + admin_user["salt"]).encode("utf-8")).hexdigest()
                    if computed_hash == admin_user["passwordHash"]:
                        token = generate_token(admin_user["username"], "ADMIN", admin_user["name"])
                        self.send_json_response({
                            "success": True,
                            "role": "ADMIN",
                            "token": token,
                            "message": "Admin authentication successful.",
                            "admin": {
                                "username": admin_user["username"],
                                "name": admin_user["name"],
                                "role": "ADMIN"
                            }
                        })
                        return
                self.send_json_response({"success": False, "message": "Invalid admin username or password."})
                return

            # 3. Admin Dashboard (Strict Role Verification)
            if action == "getAdminDashboard":
                token = payload.get("token")
                valid, err, user = verify_token(token, "ADMIN")
                if not valid:
                    self.send_json_response({"success": False, "error": "UNAUTHORIZED", "message": err}, status=403)
                    return

                today = datetime.datetime.now().strftime("%Y-%m-%d")
                recent = []
                for a in reversed(ATTENDANCE_DB[-15:]):
                    recent.append({
                        "date": a.get("date", today),
                        "time": a.get("time", "10:00:00"),
                        "cadreId": a.get("cadreId", ""),
                        "name": a.get("name", ""),
                        "cadreType": a.get("cadreType", "FMT"),
                        "activity": a.get("activity", "Field Visit"),
                        "remarks": a.get("remarks", ""),
                        "photoLink": a.get("photoLink", ""),
                        "latitude": a.get("latitude", 0),
                        "longitude": a.get("longitude", 0)
                    })

                self.send_json_response({
                    "success": True,
                    "data": {
                        "today": today,
                        "totalCadres": len(CADRE_MASTER),
                        "activeCadres": len([c for c in CADRE_MASTER if c.get("status") == "Active"]),
                        "cadreTypes": {"FMT": 1, "ICRP": 1, "T-ICRP": 1},
                        "todayFieldVisits": len([a for a in ATTENDANCE_DB if a.get("activity") == "Field Visit"]) + 8,
                        "todayMeetings": len([a for a in ATTENDANCE_DB if a.get("activity") == "Attend Meeting"]) + 4,
                        "totalFeedback": len(FEEDBACK_DB) + 15,
                        "averageRating": 4.8,
                        "recentAttendance": recent
                    }
                })
                return

            # 4. Admin All Data (Strict Role Verification)
            if action == "getAdminAllData":
                token = payload.get("token")
                valid, err, user = verify_token(token, "ADMIN")
                if not valid:
                    self.send_json_response({"success": False, "error": "UNAUTHORIZED", "message": err}, status=403)
                    return

                self.send_json_response({
                    "success": True,
                    "data": {
                        "cadres": CADRE_MASTER,
                        "totalAttendanceRecords": len(ATTENDANCE_DB) + 120,
                        "totalFeedbackRecords": len(FEEDBACK_DB) + 45
                    }
                })
                return

            # 5. Cadre Operations
            if action == "saveAttendance":
                ATTENDANCE_DB.append(payload)
                self.send_json_response({
                    "success": True,
                    "message": f"Attendance for '{payload.get('activity', 'Field Visit')}' recorded successfully."
                })
                return

            if action == "saveFeedback":
                FEEDBACK_DB.append(payload)
                self.send_json_response({"success": True, "message": "Feedback submitted successfully."})
                return

            if action == "getDashboard":
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                self.send_json_response({
                    "success": True,
                    "data": {
                        "today": today,
                        "totalFieldVisits": len(ATTENDANCE_DB) + 12,
                        "totalMeetings": 5,
                        "totalFeedback": len(FEEDBACK_DB) + 20,
                        "myAttendance": {"fieldVisitDone": True, "meetingDone": False}
                    }
                })
                return

        # Direct REST endpoints for web client mock
        if path == "/api/admin/login":
            username = payload.get("username", "").strip().lower()
            password = payload.get("password", "")
            admin_user = next((u for u in ADMIN_USERS if u["username"].lower() == username and u["status"] == "Active"), None)
            if admin_user:
                computed_hash = hashlib.sha256((password + admin_user["salt"]).encode("utf-8")).hexdigest()
                if computed_hash == admin_user["passwordHash"]:
                    token = generate_token(admin_user["username"], "ADMIN", admin_user["name"])
                    self.send_json_response({
                        "success": True,
                        "role": "ADMIN",
                        "token": token,
                        "admin": {"username": admin_user["username"], "name": admin_user["name"], "role": "ADMIN"}
                    })
                    return
            self.send_json_response({"success": False, "message": "Invalid admin credentials."}, status=401)
            return

        if path == "/api/attendance":
            ATTENDANCE_DB.append(payload)
            self.send_json_response({
                "success": True,
                "message": f"Attendance for '{payload.get('activity', 'Field Visit')}' recorded successfully."
            })
            return

        if path == "/api/feedback":
            FEEDBACK_DB.append(payload)
            self.send_json_response({"success": True, "message": "Feedback submitted successfully."})
            return

        self.send_response(404)
        self.end_headers()

    def send_json_response(self, data, status=200):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

def run():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), LocalDevHandler) as httpd:
        print(f"APCNF RBAC Local Dev Server running at: http://localhost:{PORT}")
        print("Press Ctrl+C to terminate.")
        httpd.serve_forever()

if __name__ == "__main__":
    run()
