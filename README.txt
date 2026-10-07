========================================================================
APCNF Cadre Attendance & Feedback App (v2.1)
Android Native App + Google Apps Script + Google Sheets
Organization: Andhra Pradesh Community Managed Natural Farming (RySS)
========================================================================

WHAT'S INCLUDED:
1. Google Apps Script Backend:
   - Code.gs: Dual Web App + REST API (doPost) with concurrency locking,
     strict authentication, duplicate prevention, and date normalization.
   - Index.html: Mobile-optimized Web App with client-side canvas photo
     compression (1024px JPEG, ~150KB), submit-time GPS, and star ratings.
   - appsscript.json: Manifest setting Asia/Kolkata timezone and V8 runtime.

2. Complete Native Android Studio Project (Kotlin):
   - Located in: ./android_app/
   - Features:
     • Native camera photo capture with automatic client-side compression
     • High-accuracy GPS with Google Play Services FusedLocationProviderClient
     • Offline submission queueing with auto-sync when network is restored
     • 4-dimensional star ratings for Training & Meeting Feedback
     • Dynamic server URL configuration directly in the app UI
     • Bilingual interface (English & Telugu prompts)

3. Security & Authentication Architecture Guide:
   - Refer to P0_01_STRICT_CADRE_AUTHENTICATION.md for full details on
     strict cadre API authentication, HMAC token verification, identity binding,
     and automated test verification (test_rbac.py).

========================================================================
PART 1: BACKEND DEPLOYMENT (Google Sheets + Apps Script)
========================================================================
1. Open Google Sheets (or create a blank spreadsheet for APCNF).
2. Go to: Extensions -> Apps Script.
3. Replace Code.gs with the provided Code.gs.
4. Click '+' -> HTML -> Name it 'Index' (without .html extension), paste Index.html.
5. In Project Settings (gear icon), enable "Show appsscript.json manifest file in editor",
   then paste the provided appsscript.json.
6. Click Save (Ctrl+S / Cmd+S).
7. Run 'doGet' once and grant Google authorization permissions.
8. Click Deploy -> New deployment:
   - Type: Web app
   - Description: APCNF Cadre App v2.1
   - Execute as: Me
   - Who has access: Anyone
9. Copy the Web App URL ending with '/exec'.

Cadre_Master Columns:
Cadre ID | Name | Mobile | Cadre Type (FMT/ICRP/T-ICRP) | District | Mandal | Village | VO | Status (Active)

========================================================================
PART 2: ANDROID STUDIO PROJECT (Building the Native APK)
========================================================================
1. Open Android Studio (Ladybug / Koala / Jellyfish / Hedgehog).
2. Click "Open" and select the folder:
   c:\Users\ndeam\Downloads\APCNF_Cadre_Attendance_Feedback_App_v2\android_app
3. Let Gradle sync project dependencies.
4. Build the APK:
   Build -> Build Bundle(s) / APK(s) -> Build APK(s)
5. Locate the generated APK at:
   android_app/app/build/outputs/apk/debug/app-debug.apk
6. Transfer and install 'app-debug.apk' on any Android phone (Android 7.0 to 14+).

Connecting Android App to Your Google Sheet:
- On first launch of the Android app, tap "Configure Server URL / సర్వర్ లింక్".
- Paste your deployed Google Apps Script Web App URL from Part 1.
- Log in using your Cadre ID and registered 10-digit Mobile number!
