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

# In-memory storage with realistic initial submissions for Admin Oversight
today_str = datetime.datetime.now().strftime("%Y-%m-%d")
yesterday_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

ATTENDANCE_DB = [
    {
        "date": yesterday_str,
        "time": "10:15:00",
        "cadreId": "FMT101",
        "name": "Lakshmi Devi",
        "cadreType": "FMT",
        "activity": "Attend Meeting",
        "remarks": "Gram Panchayat monthly review on organic certification & Subhash Palekar methods",
        "photoLink": "https://images.unsplash.com/photo-1595974482597-4b8da8879bc5?auto=format&fit=crop&w=600&q=80",
        "latitude": 14.6820,
        "longitude": 77.6010,
        "accuracy": 5.2
    },
    {
        "date": yesterday_str,
        "time": "14:40:00",
        "cadreId": "ICRP05",
        "name": "Ramesh Naidu",
        "cadreType": "ICRP",
        "activity": "Field Visit",
        "remarks": "Bio-resource input center inspection and Ghanajeevamrit storage audit",
        "photoLink": "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?auto=format&fit=crop&w=600&q=80",
        "latitude": 15.8290,
        "longitude": 78.0380,
        "accuracy": 4.1
    },
    {
        "date": today_str,
        "time": "09:30:15",
        "cadreId": "FMT101",
        "name": "Lakshmi Devi",
        "cadreType": "FMT",
        "activity": "Field Visit",
        "remarks": "Demonstrated Jeevamrit concoction & Navadhanya seed coating with 5 farmers in Chapiri",
        "photoLink": "https://images.unsplash.com/photo-1592982537447-7440770cbfc9?auto=format&fit=crop&w=600&q=80",
        "latitude": 14.6819,
        "longitude": 77.6006,
        "accuracy": 3.8
    },
    {
        "date": today_str,
        "time": "11:15:00",
        "cadreId": "ICRP05",
        "name": "Ramesh Naidu",
        "cadreType": "ICRP",
        "activity": "Attend Meeting",
        "remarks": "Cluster review meeting with VO leaders and SHG members in Arekal village",
        "photoLink": "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=600&q=80",
        "latitude": 15.8281,
        "longitude": 78.0373,
        "accuracy": 4.9
    },
    {
        "date": today_str,
        "time": "14:05:22",
        "cadreId": "TICRP02",
        "name": "Saraswathi Bai",
        "cadreType": "T-ICRP",
        "activity": "Field Visit",
        "remarks": "PMDS (Pre-Monsoon Dry Sowing) 365-day green cover demo in Mundlapadu",
        "photoLink": "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?auto=format&fit=crop&w=600&q=80",
        "latitude": 15.3934,
        "longitude": 79.0152,
        "accuracy": 3.4
    }
]

FEEDBACK_DB = [
    {
        "date": yesterday_str,
        "cadreId": "TICRP02",
        "name": "Saraswathi Bai",
        "cadreType": "T-ICRP",
        "training": "Natural Pest Management & Trap Crops",
        "trainer": "Sri Ramanjaneyulu",
        "contentRating": 5,
        "trainerRating": 4,
        "usefulnessRating": 5,
        "overallRating": 5,
        "suggestions": "Handbook in Telugu was very informative. Please conduct hands-on Neemasthram prep."
    },
    {
        "date": today_str,
        "cadreId": "FMT101",
        "name": "Lakshmi Devi",
        "cadreType": "FMT",
        "training": "Navadhanya & Bio-inputs Masterclass",
        "trainer": "Dr. Venkata Rao",
        "contentRating": 5,
        "trainerRating": 5,
        "usefulnessRating": 5,
        "overallRating": 5,
        "suggestions": "Excellent practical demo on Brahmastram and Agniastram preparation."
    },
    {
        "date": today_str,
        "cadreId": "ICRP05",
        "name": "Ramesh Naidu",
        "cadreType": "ICRP",
        "training": "PMDS 365 Days Green Cover Models",
        "trainer": "Smt. K. Anitha",
        "contentRating": 4,
        "trainerRating": 5,
        "usefulnessRating": 5,
        "overallRating": 4,
        "suggestions": "Requesting seed kits distribution earlier before monsoon onset in Adoni cluster."
    }
]


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

def generate_attendance_csv_and_records(from_date, to_date, activity="ALL", cadre_type="ALL"):
    headers = [
        "Date", "Time", "Cadre ID", "Cadre Name", "Cadre Type",
        "Activity", "Remarks", "Latitude", "Longitude", "Accuracy (m)", "Photo URL"
    ]
    def escape_csv(val):
        if val is None:
            return '""'
        s = str(val).replace('"', '""')
        return f'"{s}"'

    csv_lines = [",".join(escape_csv(h) for h in headers)]
    records = []

    for a in ATTENDANCE_DB:
        r_date = a.get("date", "")
        if r_date < from_date or r_date > to_date:
            continue
        if activity and activity != "ALL" and a.get("activity", "").lower() != activity.lower():
            continue
        if cadre_type and cadre_type != "ALL" and a.get("cadreType", "").upper() != cadre_type.upper():
            continue

        row = [
            a.get("date", ""),
            a.get("time", ""),
            a.get("cadreId", ""),
            a.get("name", ""),
            a.get("cadreType", ""),
            a.get("activity", ""),
            a.get("remarks", ""),
            a.get("latitude", ""),
            a.get("longitude", ""),
            a.get("accuracy", ""),
            a.get("photoLink", "")
        ]
        csv_lines.append(",".join(escape_csv(c) for c in row))
        records.append(a)

    return "\r\n".join(csv_lines), records

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

        # Direct CSV/Excel download
        if path == "/api/export/attendance" or query.get("action", [""])[0] == "downloadAttendanceCsv":
            token = query.get("token", [""])[0]
            valid, err, user = verify_token(token, "ADMIN")
            if not valid:
                self.send_json_response({"success": False, "error": "UNAUTHORIZED", "message": err}, status=403)
                return

            from_date = query.get("fromDate", ["2000-01-01"])[0]
            to_date = query.get("toDate", ["2099-12-31"])[0]
            f_act = query.get("activity", ["ALL"])[0]
            f_type = query.get("cadreType", ["ALL"])[0]

            csv_text, records = generate_attendance_csv_and_records(from_date, to_date, f_act, f_type)
            filename = f"APCNF_Attendance_{from_date}_to_{to_date}.csv"
            csv_bytes = csv_text.encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(csv_bytes)))
            self.end_headers()
            self.wfile.write(csv_bytes)
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

            # 4b. Admin Attendance Filter & Search
            if action == "getAdminAttendanceList":
                token = payload.get("token")
                valid, err, user = verify_token(token, "ADMIN")
                if not valid:
                    self.send_json_response({"success": False, "error": "UNAUTHORIZED", "message": err}, status=403)
                    return

                f_date = payload.get("date")
                f_act = payload.get("activity")
                f_type = payload.get("cadreType")
                f_q = (payload.get("query") or "").strip().lower()
                limit = min(max(int(payload.get("limit") or 100), 1), 200)

                results = []
                for a in reversed(ATTENDANCE_DB):
                    if f_date and f_date != "ALL" and a.get("date") != f_date:
                        continue
                    if f_act and f_act != "ALL" and a.get("activity", "").lower() != f_act.lower():
                        continue
                    if f_type and f_type != "ALL" and a.get("cadreType", "").upper() != f_type.upper():
                        continue
                    if f_q:
                        matched = (f_q in a.get("cadreId", "").lower() or
                                   f_q in a.get("name", "").lower() or
                                   f_q in a.get("remarks", "").lower())
                        if not matched:
                            continue
                    results.append(a)
                    if len(results) >= limit:
                        break

                self.send_json_response({"success": True, "count": len(results), "data": results})
                return

            # 4c. Admin Feedback Filter & Search
            if action == "getAdminFeedbackList":
                token = payload.get("token")
                valid, err, user = verify_token(token, "ADMIN")
                if not valid:
                    self.send_json_response({"success": False, "error": "UNAUTHORIZED", "message": err}, status=403)
                    return

                f_type = payload.get("cadreType")
                f_rating = payload.get("minRating")
                f_q = (payload.get("query") or "").strip().lower()
                limit = min(max(int(payload.get("limit") or 100), 1), 200)

                results = []
                for f in reversed(FEEDBACK_DB):
                    if f_type and f_type != "ALL" and f.get("cadreType", "").upper() != f_type.upper():
                        continue
                    if f_rating and f_rating != "ALL" and int(f.get("overallRating", 0)) < int(f_rating):
                        continue
                    if f_q:
                        matched = (f_q in f.get("cadreId", "").lower() or
                                   f_q in f.get("name", "").lower() or
                                   f_q in f.get("training", "").lower() or
                                   f_q in f.get("trainer", "").lower() or
                                   f_q in f.get("suggestions", "").lower())
                        if not matched:
                            continue
                    results.append(f)
                    if len(results) >= limit:
                        break

                self.send_json_response({"success": True, "count": len(results), "data": results})
                return

            # 4d. Admin Cadres Directory Filter & Search
            if action == "getAdminCadreList":
                token = payload.get("token")
                valid, err, user = verify_token(token, "ADMIN")
                if not valid:
                    self.send_json_response({"success": False, "error": "UNAUTHORIZED", "message": err}, status=403)
                    return

                f_type = payload.get("cadreType")
                f_status = payload.get("status")
                f_q = (payload.get("query") or "").strip().lower()

                results = []
                for c in CADRE_MASTER:
                    if f_type and f_type != "ALL" and c.get("cadreType", "").upper() != f_type.upper():
                        continue
                    if f_status and f_status != "ALL" and c.get("status", "Active").lower() != f_status.lower():
                        continue
                    if f_q:
                        matched = (f_q in c.get("cadreId", "").lower() or
                                   f_q in c.get("name", "").lower() or
                                   f_q in c.get("mobile", "") or
                                   f_q in c.get("district", "").lower() or
                                   f_q in c.get("mandal", "").lower() or
                                   f_q in c.get("village", "").lower())
                        if not matched:
                            continue
                    results.append(c)

                self.send_json_response({"success": True, "count": len(results), "data": results})
                return

            # 4e. Admin Attendance Export (Date Range From & To)
            if action == "exportAdminAttendance":
                token = payload.get("token")
                valid, err, user = verify_token(token, "ADMIN")
                if not valid:
                    self.send_json_response({"success": False, "error": "UNAUTHORIZED", "message": err}, status=403)
                    return

                from_date = payload.get("fromDate") or "2000-01-01"
                to_date = payload.get("toDate") or "2099-12-31"
                f_act = payload.get("activity") or "ALL"
                f_type = payload.get("cadreType") or "ALL"

                csv_text, records = generate_attendance_csv_and_records(from_date, to_date, f_act, f_type)
                filename = f"APCNF_Attendance_{from_date}_to_{to_date}.csv"

                self.send_json_response({
                    "success": True,
                    "filename": filename,
                    "fromDate": from_date,
                    "toDate": to_date,
                    "count": len(records),
                    "sheetUrl": "https://docs.google.com/spreadsheets/d/mock_apcnf_master_sheet",
                    "csvContent": csv_text,
                    "data": records
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
