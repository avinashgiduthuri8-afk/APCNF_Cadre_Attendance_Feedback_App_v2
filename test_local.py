import urllib.request
import urllib.parse
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(name, url, method="GET", payload=None):
    print(f"\n--- Testing {name} ---")
    req = urllib.request.Request(url, method=method)
    if payload:
        data = json.dumps(payload).encode("utf-8")
        req.add_header("Content-Type", "application/json")
        req.data = data
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.status
            body = response.read().decode("utf-8")
            print(f"Status: {status}")
            try:
                parsed = json.loads(body)
                print(f"Response JSON: {json.dumps(parsed, indent=2)}")
            except Exception:
                print(f"Response: {body[:150]}... (HTML content length: {len(body)})")
            return status == 200
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def main():
    results = {}
    
    # 1. Web App HTML Root
    results["Web App Root"] = test_endpoint("Web App HTML Root", f"{BASE_URL}/")

    # 2. Mock API: Login / Cadre lookup
    results["Cadre Lookup"] = test_endpoint(
        "Cadre Verification (FMT101)",
        f"{BASE_URL}/api/cadre?id=FMT101&mobile=9876543210"
    )

    # 3. Mock API: Submit Attendance
    att_payload = {
        "cadreId": "FMT101",
        "name": "Lakshmi Devi",
        "mobile": "9876543210",
        "cadreType": "FMT",
        "activity": "Field Visit",
        "remarks": "PMDS field visit in Chapiri village",
        "photoBase64": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
        "latitude": 14.6819,
        "longitude": 77.6006,
        "accuracy": 12.5
    }
    results["Save Attendance"] = test_endpoint(
        "Submit Attendance",
        f"{BASE_URL}/api/attendance",
        method="POST",
        payload=att_payload
    )

    # 4. Mock API: Submit Feedback
    fb_payload = {
        "cadreId": "FMT101",
        "name": "Lakshmi Devi",
        "mobile": "9876543210",
        "cadreType": "FMT",
        "training": "PMDS Natural Farming",
        "trainer": "Sri Ramana Garu",
        "contentRating": 5,
        "trainerRating": 5,
        "usefulnessRating": 5,
        "overallRating": 5,
        "suggestions": "Very clear practical demonstration"
    }
    results["Save Feedback"] = test_endpoint(
        "Submit Feedback",
        f"{BASE_URL}/api/feedback",
        method="POST",
        payload=fb_payload
    )

    # 5. Mock API: Dashboard
    results["Dashboard"] = test_endpoint(
        "Dashboard Statistics",
        f"{BASE_URL}/api/dashboard?cadreId=FMT101"
    )

    # 6. Android App Endpoint: POST /exec (Login)
    results["Android API Login (/exec)"] = test_endpoint(
        "Android REST API: Login",
        f"{BASE_URL}/exec",
        method="POST",
        payload={"action": "login", "cadreId": "FMT101", "mobile": "9876543210"}
    )

    # 7. Android App Endpoint: POST /exec (Save Attendance)
    results["Android API Attendance (/exec)"] = test_endpoint(
        "Android REST API: Save Attendance",
        f"{BASE_URL}/exec",
        method="POST",
        payload={"action": "saveAttendance", **att_payload}
    )

    print("\n================== TEST SUMMARY ==================")
    all_passed = True
    for k, v in results.items():
        status_str = "PASSED" if v else "FAILED"
        print(f"  {k}: {status_str}")
        if not v:
            all_passed = False
    print("==================================================")
    print(f"Overall Result: {'ALL TESTS PASSED (7/7)' if all_passed else 'SOME TESTS FAILED'}")

if __name__ == "__main__":
    main()
