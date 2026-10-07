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
    print("PROJECT APCNF — RBAC STRICT CADRE & ADMIN TEST SUITE")
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
    print("\n[TEST 4A] Testing Unauthenticated access to Admin API (No Token)...")
    status, res = send_request({
        "action": "getAdminDashboard"
    })
    t4a_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (No Token): {'PASSED (Access Denied)' if t4a_pass else 'FAILED'}")

    print("[TEST 4B] Testing Tampered / Invalid Token on Admin API...")
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
    print(f"  Result (Admin Dashboard): {'PASSED' if t5a_pass else 'FAILED'} (Total Cadres: {dash_data.get('totalCadres')})")

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
    # TEST 6: Valid CADRE token on Cadre Endpoints -> ALLOWED
    # ------------------------------------------------------------------
    print("\n[TEST 6A] Testing Cadre Attendance submission with Valid Cadre Token...")
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

    print("[TEST 6B] Testing Cadre Feedback submission with Valid Cadre Token...")
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

    print("[TEST 6C] Testing Cadre Dashboard fetch with Valid Cadre Token...")
    status, res = send_request({
        "action": "getDashboard",
        "token": cadre_token,
        "cadreId": "FMT101"
    })
    t6c_pass = (status == 200 and res.get("success") is True and "data" in res)
    print(f"  Result (Dashboard): {'PASSED' if t6c_pass else 'FAILED'} (HasData: {'data' in res})")
    test_results.append(("6. Valid CADRE token -> ALLOWED on Cadre endpoints", t6a_pass and t6b_pass and t6c_pass))

    # ------------------------------------------------------------------
    # TEST 7: No-Token Cadre request -> DENIED
    # ------------------------------------------------------------------
    print("\n[TEST 7A] Testing saveAttendance without token -> DENIED...")
    status, res = send_request({
        "action": "saveAttendance",
        "cadreId": "FMT101",
        "activity": "Field Visit"
    })
    t7a_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (saveAttendance no token): {'PASSED (Denied)' if t7a_pass else 'FAILED'}")

    print("[TEST 7B] Testing saveFeedback without token -> DENIED...")
    status, res = send_request({
        "action": "saveFeedback",
        "cadreId": "FMT101",
        "training": "PMDS",
        "overallRating": 5
    })
    t7b_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (saveFeedback no token): {'PASSED (Denied)' if t7b_pass else 'FAILED'}")

    print("[TEST 7C] Testing getDashboard without token -> DENIED...")
    status, res = send_request({
        "action": "getDashboard",
        "cadreId": "FMT101"
    })
    t7c_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (getDashboard no token): {'PASSED (Denied)' if t7c_pass else 'FAILED'}")
    test_results.append(("7. No-token Cadre requests -> DENIED", t7a_pass and t7b_pass and t7c_pass))

    # ------------------------------------------------------------------
    # TEST 8: Fake/invalid token on Cadre requests -> DENIED
    # ------------------------------------------------------------------
    fake_token = "fake.invalid.cadre_token"
    print("\n[TEST 8A] Testing saveAttendance with fake token -> DENIED...")
    status, res = send_request({
        "action": "saveAttendance",
        "token": fake_token,
        "cadreId": "FMT101",
        "activity": "Field Visit"
    })
    t8a_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (saveAttendance fake token): {'PASSED (Denied)' if t8a_pass else 'FAILED'}")

    print("[TEST 8B] Testing saveFeedback with fake token -> DENIED...")
    status, res = send_request({
        "action": "saveFeedback",
        "token": fake_token,
        "cadreId": "FMT101",
        "training": "PMDS",
        "overallRating": 5
    })
    t8b_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (saveFeedback fake token): {'PASSED (Denied)' if t8b_pass else 'FAILED'}")

    print("[TEST 8C] Testing getDashboard with fake token -> DENIED...")
    status, res = send_request({
        "action": "getDashboard",
        "token": fake_token,
        "cadreId": "FMT101"
    })
    t8c_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (getDashboard fake token): {'PASSED (Denied)' if t8c_pass else 'FAILED'}")
    test_results.append(("8. Fake/invalid token on Cadre requests -> DENIED", t8a_pass and t8b_pass and t8c_pass))

    # ------------------------------------------------------------------
    # TEST 9: Identity binding: Valid CADRE token + different cadreId -> DENIED
    # ------------------------------------------------------------------
    print("\n[TEST 9A] Testing saveAttendance with token for FMT101 but payload cadreId ICRP05 -> DENIED...")
    status, res = send_request({
        "action": "saveAttendance",
        "token": cadre_token,
        "cadreId": "ICRP05",  # Mismatched ID!
        "activity": "Field Visit"
    })
    t9a_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (saveAttendance ID mismatch): {'PASSED (Denied)' if t9a_pass else 'FAILED'}")

    print("[TEST 9B] Testing saveFeedback with token for FMT101 but payload cadreId ICRP05 -> DENIED...")
    status, res = send_request({
        "action": "saveFeedback",
        "token": cadre_token,
        "cadreId": "ICRP05",  # Mismatched ID!
        "training": "PMDS",
        "overallRating": 5
    })
    t9b_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (saveFeedback ID mismatch): {'PASSED (Denied)' if t9b_pass else 'FAILED'}")

    print("[TEST 9C] Testing getDashboard with token for FMT101 but payload cadreId ICRP05 -> DENIED...")
    status, res = send_request({
        "action": "getDashboard",
        "token": cadre_token,
        "cadreId": "ICRP05"  # Mismatched ID!
    })
    t9c_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (getDashboard ID mismatch): {'PASSED (Denied)' if t9c_pass else 'FAILED'}")
    test_results.append(("9. Valid CADRE token + different cadreId -> DENIED", t9a_pass and t9b_pass and t9c_pass))

    # ------------------------------------------------------------------
    # TEST 10: Valid ADMIN token calling Cadre-only endpoint -> DENIED
    # ------------------------------------------------------------------
    print("\n[TEST 10A] Testing saveAttendance with ADMIN token -> DENIED...")
    status, res = send_request({
        "action": "saveAttendance",
        "token": admin_token,
        "cadreId": "FMT101",
        "activity": "Field Visit"
    })
    t10a_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (saveAttendance with Admin Token): {'PASSED (Denied)' if t10a_pass else 'FAILED'}")

    print("[TEST 10B] Testing saveFeedback with ADMIN token -> DENIED...")
    status, res = send_request({
        "action": "saveFeedback",
        "token": admin_token,
        "cadreId": "FMT101",
        "training": "PMDS",
        "overallRating": 5
    })
    t10b_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (saveFeedback with Admin Token): {'PASSED (Denied)' if t10b_pass else 'FAILED'}")

    print("[TEST 10C] Testing getDashboard with ADMIN token -> DENIED...")
    status, res = send_request({
        "action": "getDashboard",
        "token": admin_token,
        "cadreId": "FMT101"
    })
    t10c_pass = (status in [401, 403] or res.get("success") is False)
    print(f"  Result (getDashboard with Admin Token): {'PASSED (Denied)' if t10c_pass else 'FAILED'}")
    test_results.append(("10. Valid ADMIN token calling Cadre-only endpoint -> DENIED", t10a_pass and t10b_pass and t10c_pass))

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("RBAC & CADRE AUTHENTICATION TEST SUMMARY")
    print("=" * 60)
    all_ok = True
    for name, passed in test_results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        if not passed:
            all_ok = False
    print("=" * 60)
    total_tests = len(test_results)
    passed_count = sum(1 for _, p in test_results if p)
    print(f"OVERALL RESULT: {passed_count}/{total_tests} TESTS PASSED")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
