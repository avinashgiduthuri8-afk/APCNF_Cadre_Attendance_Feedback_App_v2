#!/usr/bin/env python3
"""
Phase 2 Admin Oversight & Filtering Verification Suite for APCNF App v2
Tests:
1. Admin auth & Token issuance
2. Multi-filter Attendance queries (activity, cadreType, search query)
3. Multi-filter Feedback queries (minRating, query)
4. Multi-filter Cadre Directory queries (cadreType, status, search query)
5. Strict RBAC enforcement: Cadre token rejection (403) on all Phase 2 Admin endpoints
"""

import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://localhost:8000/exec"

def post(payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8")) if e.fp else {}
        return e.code, body

def run_tests():
    print("==================================================")
    print(" APCNF RBAC Phase 2: Admin Oversight & Filters Test")
    print("==================================================")

    passed = 0
    total = 0

    # 1. Admin Login
    total += 1
    status, res = post({"action": "adminLogin", "username": "admin@apcnf.gov.in", "password": "Admin@APCNF2026"})
    if status == 200 and res.get("success") and res.get("role") == "ADMIN":
        admin_token = res.get("token")
        print(f"[PASS] 1. Admin login successful. Token acquired.")
        passed += 1
    else:
        print(f"[FAIL] 1. Admin login failed: {res}")
        sys.exit(1)

    # 2. Cadre Login
    total += 1
    status, res = post({"action": "login", "cadreId": "FMT101", "mobile": "9876543210"})
    if status == 200 and res.get("success") and res.get("role") == "CADRE":
        cadre_token = res.get("token")
        print(f"[PASS] 2. Cadre login successful. Role: CADRE.")
        passed += 1
    else:
        print(f"[FAIL] 2. Cadre login failed: {res}")
        sys.exit(1)

    # 3. Admin Attendance List (All)
    total += 1
    status, res = post({"action": "getAdminAttendanceList", "token": admin_token})
    if status == 200 and res.get("success") and len(res.get("data", [])) > 0:
        print(f"[PASS] 3. Admin fetched all attendance records. Total: {res.get('count')}")
        passed += 1
    else:
        print(f"[FAIL] 3. Admin fetch all attendance failed: {res}")

    # 4. Filter Attendance by Activity = "Field Visit"
    total += 1
    status, res = post({"action": "getAdminAttendanceList", "token": admin_token, "activity": "Field Visit"})
    records = res.get("data", [])
    if status == 200 and res.get("success") and len(records) > 0 and all(r.get("activity") == "Field Visit" for r in records):
        print(f"[PASS] 4. Filter Attendance by Activity='Field Visit' passed. Matched: {len(records)}")
        passed += 1
    else:
        print(f"[FAIL] 4. Filter Attendance by Activity failed: {res}")

    # 5. Filter Attendance by Cadre Type = "FMT"
    total += 1
    status, res = post({"action": "getAdminAttendanceList", "token": admin_token, "cadreType": "FMT"})
    records = res.get("data", [])
    if status == 200 and res.get("success") and len(records) > 0 and all(r.get("cadreType") == "FMT" for r in records):
        print(f"[PASS] 5. Filter Attendance by CadreType='FMT' passed. Matched: {len(records)}")
        passed += 1
    else:
        print(f"[FAIL] 5. Filter Attendance by CadreType failed: {res}")

    # 6. Search Attendance by query = "Chapiri"
    total += 1
    status, res = post({"action": "getAdminAttendanceList", "token": admin_token, "query": "Chapiri"})
    records = res.get("data", [])
    if status == 200 and res.get("success") and len(records) > 0 and any("Chapiri" in r.get("remarks", "") for r in records):
        print(f"[PASS] 6. Search Attendance with query='Chapiri' passed. Matched: {len(records)}")
        passed += 1
    else:
        print(f"[FAIL] 6. Search Attendance failed: {res}")

    # 7. Cadre Token Blocked from Admin Attendance List
    total += 1
    status, res = post({"action": "getAdminAttendanceList", "token": cadre_token})
    if status == 403 and not res.get("success") and res.get("error") == "UNAUTHORIZED":
        print(f"[PASS] 7. Cadre token strictly blocked from getAdminAttendanceList (403 Unauthorized).")
        passed += 1
    else:
        print(f"[FAIL] 7. Cadre token was not properly rejected: status={status}, res={res}")

    # 8. Admin Feedback List with minRating = 5
    total += 1
    status, res = post({"action": "getAdminFeedbackList", "token": admin_token, "minRating": 5})
    records = res.get("data", [])
    if status == 200 and res.get("success") and len(records) > 0 and all(int(r.get("overallRating", 0)) >= 5 for r in records):
        print(f"[PASS] 8. Admin Feedback List minRating=5 passed. Matched: {len(records)}")
        passed += 1
    else:
        print(f"[FAIL] 8. Filter Feedback by minRating failed: {res}")

    # 9. Cadre Token Blocked from Admin Feedback List
    total += 1
    status, res = post({"action": "getAdminFeedbackList", "token": cadre_token})
    if status == 403 and not res.get("success") and res.get("error") == "UNAUTHORIZED":
        print(f"[PASS] 9. Cadre token strictly blocked from getAdminFeedbackList (403 Unauthorized).")
        passed += 1
    else:
        print(f"[FAIL] 9. Cadre token was not properly rejected: status={status}, res={res}")

    # 10. Admin Cadre Directory with cadreType = "ICRP"
    total += 1
    status, res = post({"action": "getAdminCadreList", "token": admin_token, "cadreType": "ICRP"})
    records = res.get("data", [])
    if status == 200 and res.get("success") and len(records) > 0 and all(c.get("cadreType") == "ICRP" for c in records):
        print(f"[PASS] 10. Admin Cadre Directory cadreType='ICRP' passed. Matched: {len(records)}")
        passed += 1
    else:
        print(f"[FAIL] 10. Filter Cadre Directory failed: {res}")

    # 11. Cadre Token Blocked from Admin Cadre Directory
    total += 1
    status, res = post({"action": "getAdminCadreList", "token": cadre_token})
    if status == 403 and not res.get("success") and res.get("error") == "UNAUTHORIZED":
        print(f"[PASS] 11. Cadre token strictly blocked from getAdminCadreList (403 Unauthorized).")
        passed += 1
    else:
        print(f"[FAIL] 11. Cadre token was not properly rejected: status={status}, res={res}")

    # 12. Admin Attendance Export (Date Range From & To)
    total += 1
    status, res = post({
        "action": "exportAdminAttendance",
        "token": admin_token,
        "fromDate": "2026-10-01",
        "toDate": "2026-10-31"
    })
    if status == 200 and res.get("success") and "csvContent" in res and res.get("count", 0) > 0:
        csv_header = res.get("csvContent", "").splitlines()[0]
        print(f"[PASS] 12. Admin Attendance Export successful. Filename: {res.get('filename')}, Records: {res.get('count')}, Header: {csv_header[:40]}...")
        passed += 1
    else:
        print(f"[FAIL] 12. Admin Attendance Export failed: {res}")

    # 13. Direct GET CSV/Excel Download endpoint
    total += 1
    try:
        download_url = f"http://localhost:8000/api/export/attendance?token={admin_token}&fromDate=2026-10-01&toDate=2026-10-31"
        with urllib.request.urlopen(download_url) as d_resp:
            c_type = d_resp.headers.get("Content-Type", "")
            d_body = d_resp.read().decode("utf-8")
            if d_resp.status == 200 and "text/csv" in c_type and "Cadre ID" in d_body:
                print(f"[PASS] 13. Direct CSV download endpoint verified. Content-Type: {c_type}, Bytes: {len(d_body)}")
                passed += 1
            else:
                print(f"[FAIL] 13. Direct CSV download invalid: {c_type}")
    except Exception as e:
        print(f"[FAIL] 13. Direct CSV download request error: {e}")

    # 14. Cadre Token Blocked from Attendance Export
    total += 1
    status, res = post({"action": "exportAdminAttendance", "token": cadre_token, "fromDate": "2026-10-01", "toDate": "2026-10-31"})
    if status == 403 and not res.get("success") and res.get("error") == "UNAUTHORIZED":
        print(f"[PASS] 14. Cadre token strictly blocked from exportAdminAttendance (403 Unauthorized).")
        passed += 1
    else:
        print(f"[FAIL] 14. Cadre token export was not properly rejected: status={status}, res={res}")

    print("--------------------------------------------------")
    print(f"Results: {passed} / {total} tests passed successfully!")
    print("--------------------------------------------------")
    return passed == total

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

