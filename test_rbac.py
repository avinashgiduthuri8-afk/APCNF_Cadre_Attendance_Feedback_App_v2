import urllib.request
import urllib.parse
import json
import sys

BASE_URL = "http://localhost:8000/exec"

def send_request(payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}
    except Exception as e:
        return 500, {"error": str(e)}

def main():
    print("==================================================")
    print("PROJECT APCNF — RBAC PHASE 1 AUTOMATED TEST SUITE")
    print("==================================================")

    test_results = []

    # ------------------------------------------------------------------
    # TEST 1: Cadre login -> Cadre role & token
    # ------------------------------------------------------------------
    print("\n[TEST 1] Testing Cadre Login (FMT101 / 9876543210)...")
    status, res = send_request({
        "action": "login",
        "cadreId": "FMT101",
        "mobile": "9876543210"
    })
    cadre_token = res.get("token")
    cadre_role = res.get("role")
    t1_pass = (status == 200 and res.get("success") is True and cadre_role == "CADRE" and cadre_token is not None)
    print(f"  Result: {'PASSED' if t1_pass else 'FAILED'} (Role: {cadre_role}, HasToken: {bool(cadre_token)})")
    test_results.append(("1. Cadre login -> returns CADRE role and token", t1_pass))

    # ------------------------------------------------------------------
    # TEST 2: Admin login -> Admin role & token
    # ------------------------------------------------------------------
    print("\n[TEST 2] Testing Admin Login (admin@apcnf.gov.in / Admin@APCNF2026)...")
    status, res = send_request({
        "action": "adminLogin",
        "username": "admin@apcnf.gov.in",
        "password": "Admin@APCNF2026"
    })
    admin_token = res.get("token")
    admin_role = res.get("role")
    t2_pass = (status == 200 and res.get("success") is True and admin_role == "ADMIN" and admin_token is not None)
    print(f"  Result: {'PASSED' if t2_pass else 'FAILED'} (Role: {admin_role}, HasToken: {bool(admin_token)})")
    test_results.append(("2. Admin login -> returns ADMIN role and token", t2_pass))

    # ------------------------------------------------------------------
    # TEST 3: Cadre CANNOT access Admin APIs (Forbidden with Cadre Token)
    # ------------------------------------------------------------------
    print("\n[TEST 3] Testing Authorization Barrier: Cadre attempting to access Admin Dashboard...")
    status, res = send_request({
        "action": "getAdminDashboard",
        "token": cadre_token
    })
    t3_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result: {'PASSED (Access Correctly Denied)' if t3_pass else 'FAILED (Security Breach!)'}")
    print(f"  Server Message: {res.get('message', res.get('error'))}")
    test_results.append(("3. Cadre token CANNOT access Admin Dashboard API", t3_pass))

    # ------------------------------------------------------------------
    # TEST 4: Unauthenticated user CANNOT access Admin APIs
    # ------------------------------------------------------------------
    print("\n[TEST 4A] Testing Unauthenticated access (No Token)...")
    status, res = send_request({
        "action": "getAdminDashboard"
    })
    t4a_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (No Token): {'PASSED (Access Denied)' if t4a_pass else 'FAILED'}")

    print("[TEST 4B] Testing Tampered / Invalid Token...")
    status, res = send_request({
        "action": "getAdminDashboard",
        "token": "fake.jwt.token_attempting_privilege_escalation"
    })
    t4b_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (Fake Token): {'PASSED (Access Denied)' if t4b_pass else 'FAILED'}")
    test_results.append(("4. Unauthenticated / forged token CANNOT access Admin APIs", t4a_pass and t4b_pass))

    # ------------------------------------------------------------------
    # TEST 5: Admin CAN access authorized Admin APIs
    # ------------------------------------------------------------------
    print("\n[TEST 5A] Testing Admin Dashboard with valid Admin Token...")
    status, res = send_request({
        "action": "getAdminDashboard",
        "token": admin_token
    })
    dash_data = res.get("data", {})
    t5a_pass = (status == 200 and res.get("success") is True and "totalCadres" in dash_data)
    print(f"  Result (Admin Dashboard): {'PASSED' if t5a_pass else 'FAILED'} (Total Cadres: {dash_data.get('totalCadres')}, Field Visits: {dash_data.get('todayFieldVisits')})")

    print("[TEST 5B] Testing Admin All-Data API with valid Admin Token...")
    status, res = send_request({
        "action": "getAdminAllData",
        "token": admin_token
    })
    all_data = res.get("data", {})
    t5b_pass = (status == 200 and res.get("success") is True and "cadres" in all_data)
    print(f"  Result (Admin All Data): {'PASSED' if t5b_pass else 'FAILED'} (Cadres count: {len(all_data.get('cadres', []))})")
    test_results.append(("5. Admin CAN access authorized Admin APIs", t5a_pass and t5b_pass))

    # ------------------------------------------------------------------
    # TEST 6: Existing Cadre Attendance & Feedback still works
    # ------------------------------------------------------------------
    print("\n[TEST 6A] Testing Cadre Attendance submission with Cadre Token...")
    status, res = send_request({
        "action": "saveAttendance",
        "token": cadre_token,
        "cadreId": "FMT101",
        "name": "Lakshmi Devi",
        "mobile": "9876543210",
        "cadreType": "FMT",
        "activity": "Field Visit",
        "remarks": "PMDS field visit verification in Chapiri",
        "photoBase64": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
        "latitude": 14.6819,
        "longitude": 77.6006,
        "accuracy": 15.0
    })
    t6a_pass = (status == 200 and res.get("success") is True)
    print(f"  Result (Attendance): {'PASSED' if t6a_pass else 'FAILED'} (Msg: {res.get('message')})")

    print("[TEST 6B] Testing Cadre Feedback submission with Cadre Token...")
    status, res = send_request({
        "action": "saveFeedback",
        "token": cadre_token,
        "cadreId": "FMT101",
        "name": "Lakshmi Devi",
        "mobile": "9876543210",
        "cadreType": "FMT",
        "training": "PMDS & Navadhanya Practices",
        "trainer": "Sri Ramana Garu",
        "contentRating": 5,
        "trainerRating": 5,
        "usefulnessRating": 5,
        "overallRating": 5,
        "suggestions": "Very clear practical demonstration"
    })
    t6b_pass = (status == 200 and res.get("success") is True)
    print(f"  Result (Feedback): {'PASSED' if t6b_pass else 'FAILED'} (Msg: {res.get('message')})")
    test_results.append(("6. Existing Cadre attendance & feedback flow intact", t6a_pass and t6b_pass))

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("RBAC PHASE 1 TEST SUMMARY")
    print("=" * 60)
    all_ok = True
    for name, passed in test_results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        if not passed:
            all_ok = False
    print("=" * 60)
    print(f"OVERALL RESULT: {'ALL RBAC TESTS PASSED (6/6)' if all_ok else 'SOME TESTS FAILED'}")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
