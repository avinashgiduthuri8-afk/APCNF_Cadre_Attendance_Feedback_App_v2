#!/usr/bin/env python3
"""
Localhost Mock Server for APCNF Cadre Attendance & Feedback App v2
Serves the web client and simulates both the Google Apps Script Web App environment
and the REST API endpoint (doPost) for testing the Android App locally.
"""

import http.server
import socketserver
import json
import urllib.parse
import os
import datetime

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Sample Master Cadre Data matching Cadre_Master in Google Sheets
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

# In-memory storage for test submissions
ATTENDANCE_DB = []
FEEDBACK_DB = []

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
            
            self.send_json_response({"success": matched is not None, "cadre": matched})
            return

        # Mock API: Dashboard
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

        # Default static file serving
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

            if action == "login":
                cid = payload.get("cadreId", "").strip().upper()
                mob = payload.get("mobile", "").strip()[-10:]
                matched = next((c for c in CADRE_MASTER if c["cadreId"].upper() == cid and c["mobile"][-10:] == mob), None)
                if matched:
                    self.send_json_response({"success": True, "message": "Login successful.", "cadre": matched})
                else:
                    self.send_json_response({"success": False, "message": "Cadre not found. Check Cadre ID and Mobile."})
                return

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

    def send_json_response(self, data):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def run():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), LocalDevHandler) as httpd:
        print(f"APCNF Local Dev Server running at: http://localhost:{PORT}")
        print("Press Ctrl+C to terminate.")
        httpd.serve_forever()

if __name__ == "__main__":
    run()
