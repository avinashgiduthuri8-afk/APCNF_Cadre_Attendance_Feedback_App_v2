/**
 * APCNF Cadre Attendance & Feedback App (v2.1)
 * Backend: Google Apps Script + Google Sheets + Google Drive
 * Role-Based Access Control (RBAC): CADRE & ADMIN roles
 * Organization: Andhra Pradesh Community Managed Natural Farming (RySS)
 */

const CONFIG = {
  APP_NAME: "APCNF Cadre Attendance & Feedback",
  VERSION: "2.2.0-RBAC",
  TIMEZONE: "Asia/Kolkata",
  CADRE_TYPES: ["FMT", "ICRP", "T-ICRP"],
  ACTIVITIES: ["Field Visit", "Attend Meeting"],
  ROLES: {
    CADRE: "CADRE",
    ADMIN: "ADMIN"
  },
  SHEETS: {
    CADRES: "Cadre_Master",
    ATTENDANCE: "Attendance",
    FEEDBACK: "Feedback",
    ADMINS: "Admin_Users"
  },
  PHOTO_FOLDER: "APCNF Cadre Attendance Photos"
};

let _sheetsInitialized = false;

/**
 * Web App entry point for web browsers.
 */
function doGet(e) {
  setupSheets_();
  
  if (e && e.parameter && e.parameter.action === "status") {
    return jsonResponse_({
      status: "online",
      appName: CONFIG.APP_NAME,
      version: CONFIG.VERSION,
      serverTime: Utilities.formatDate(new Date(), CONFIG.TIMEZONE, "yyyy-MM-dd HH:mm:ss")
    });
  }

  // Direct CSV/Excel download endpoint for browser & export links
  if (e && e.parameter && e.parameter.action === "downloadAttendanceCsv") {
    try {
      verifyToken_(e.parameter.token, CONFIG.ROLES.ADMIN);
      const res = exportAdminAttendanceCsv_(e.parameter);
      return ContentService.createTextOutput(res.csvContent)
        .setMimeType(ContentService.MimeType.CSV)
        .downloadAsFile(res.filename);
    } catch (err) {
      return jsonResponse_({ success: false, error: "UNAUTHORIZED", message: err.message });
    }
  }

  return HtmlService.createTemplateFromFile("Index")
    .evaluate()
    .setTitle(CONFIG.APP_NAME)
    .addMetaTag("viewport", "width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.DEFAULT);
}

/**
 * REST API entry point for Native Android App and Web Client.
 * All Admin requests strictly verify server-side authorization.
 */
function doPost(e) {
  setupSheets_();
  try {
    let payload = {};
    if (e && e.postData && e.postData.contents) {
      payload = JSON.parse(e.postData.contents);
    } else if (e && e.parameter) {
      payload = e.parameter;
    }

    const action = payload.action;

    switch (action) {
      // --- 1. Cadre Authentication ---
      case "login": {
        const cadre = getCadre(payload.cadreId, payload.mobile);
        if (!cadre) {
          return jsonResponse_({ success: false, message: "Cadre not found. Verify Cadre ID and Mobile Number." });
        }
        if (String(cadre.status || "Active").toLowerCase() !== "active") {
          return jsonResponse_({ success: false, message: "Cadre status is inactive. Contact Mandal Incharge." });
        }
        // Issue Cadre Session Token
        const token = generateToken_(cadre.cadreId, CONFIG.ROLES.CADRE, cadre.name, {
          mobile: cadre.mobile,
          cadreType: cadre.cadreType
        });
        return jsonResponse_({
          success: true,
          role: CONFIG.ROLES.CADRE,
          token: token,
          message: "Cadre authentication successful.",
          cadre: cadre
        });
      }

      // --- 2. Admin Authentication (Server-Side) ---
      case "adminLogin": {
        const username = String(payload.username || "").trim();
        const password = String(payload.password || "");
        if (!username || !password) {
          return jsonResponse_({ success: false, message: "Username and password are required." });
        }
        const adminUser = authenticateAdmin_(username, password);
        if (!adminUser) {
          return jsonResponse_({ success: false, message: "Invalid admin credentials." });
        }
        // Issue Admin Session Token (24h lifespan)
        const token = generateToken_(adminUser.username, CONFIG.ROLES.ADMIN, adminUser.name);
        return jsonResponse_({
          success: true,
          role: CONFIG.ROLES.ADMIN,
          token: token,
          message: "Admin authentication successful.",
          admin: {
            username: adminUser.username,
            name: adminUser.name,
            role: CONFIG.ROLES.ADMIN
          }
        });
      }

      // --- 3. Cadre Operations (Strict Token Auth & Identity Binding) ---
      case "saveAttendance": {
        if (!payload.token) {
          return jsonResponse_({ success: false, error: "UNAUTHORIZED", message: "Authentication token required." });
        }
        const auth = verifyToken_(payload.token, CONFIG.ROLES.CADRE);
        const authCadreId = String(auth.sub || "").trim().toUpperCase();
        if (payload.cadreId) {
          const clientCadreId = String(payload.cadreId).trim().toUpperCase();
          if (clientCadreId !== authCadreId) {
            return jsonResponse_({ success: false, error: "UNAUTHORIZED", message: "Token identity mismatch. Client cadreId does not match authenticated user." });
          }
        }
        const verifiedCadre = getCadreById_(authCadreId);
        if (!verifiedCadre || String(verifiedCadre.status || "").toLowerCase() !== "active") {
          return jsonResponse_({ success: false, error: "UNAUTHORIZED", message: "Authenticated cadre is not active or not found." });
        }
        payload.cadreId = verifiedCadre.cadreId;
        payload.name = verifiedCadre.name;
        payload.mobile = verifiedCadre.mobile;
        payload.cadreType = verifiedCadre.cadreType;

        const result = saveAttendance(payload);
        return jsonResponse_({ success: true, message: result.message, timestamp: new Date().toISOString() });
      }

      case "saveFeedback": {
        if (!payload.token) {
          return jsonResponse_({ success: false, error: "UNAUTHORIZED", message: "Authentication token required." });
        }
        const auth = verifyToken_(payload.token, CONFIG.ROLES.CADRE);
        const authCadreId = String(auth.sub || "").trim().toUpperCase();
        if (payload.cadreId) {
          const clientCadreId = String(payload.cadreId).trim().toUpperCase();
          if (clientCadreId !== authCadreId) {
            return jsonResponse_({ success: false, error: "UNAUTHORIZED", message: "Token identity mismatch. Client cadreId does not match authenticated user." });
          }
        }
        const verifiedCadre = getCadreById_(authCadreId);
        if (!verifiedCadre || String(verifiedCadre.status || "").toLowerCase() !== "active") {
          return jsonResponse_({ success: false, error: "UNAUTHORIZED", message: "Authenticated cadre is not active or not found." });
        }
        payload.cadreId = verifiedCadre.cadreId;
        payload.name = verifiedCadre.name;
        payload.mobile = verifiedCadre.mobile;
        payload.cadreType = verifiedCadre.cadreType;

        const result = saveFeedback(payload);
        return jsonResponse_({ success: true, message: result.message, timestamp: new Date().toISOString() });
      }

      case "getDashboard": {
        if (!payload.token) {
          return jsonResponse_({ success: false, error: "UNAUTHORIZED", message: "Authentication token required." });
        }
        const auth = verifyToken_(payload.token, CONFIG.ROLES.CADRE);
        const authCadreId = String(auth.sub || "").trim().toUpperCase();
        if (payload.cadreId) {
          const clientCadreId = String(payload.cadreId).trim().toUpperCase();
          if (clientCadreId !== authCadreId) {
            return jsonResponse_({ success: false, error: "UNAUTHORIZED", message: "Token identity mismatch. Client cadreId does not match authenticated user." });
          }
        }
        const dash = getDashboard(authCadreId);
        return jsonResponse_({ success: true, data: dash });
      }

      // --- 4. Admin Data APIs (Strict Server-Side Authorization) ---
      case "getAdminDashboard": {
        verifyToken_(payload.token, CONFIG.ROLES.ADMIN);
        const adminDash = getAdminDashboardData_();
        return jsonResponse_({ success: true, data: adminDash });
      }

      case "getAdminAllData": {
        verifyToken_(payload.token, CONFIG.ROLES.ADMIN);
        const allData = getAdminAllData_();
        return jsonResponse_({ success: true, data: allData });
      }

      case "getAdminAttendanceList": {
        verifyToken_(payload.token, CONFIG.ROLES.ADMIN);
        const records = getAdminAttendanceList_(payload);
        return jsonResponse_({ success: true, count: records.length, data: records });
      }

      case "getAdminFeedbackList": {
        verifyToken_(payload.token, CONFIG.ROLES.ADMIN);
        const records = getAdminFeedbackList_(payload);
        return jsonResponse_({ success: true, count: records.length, data: records });
      }

      case "getAdminCadreList": {
        verifyToken_(payload.token, CONFIG.ROLES.ADMIN);
        const cadres = getAdminCadreList_(payload);
        return jsonResponse_({ success: true, count: cadres.length, data: cadres });
      }

      case "exportAdminAttendance": {
        verifyToken_(payload.token, CONFIG.ROLES.ADMIN);
        const exportData = exportAdminAttendanceCsv_(payload);
        return jsonResponse_({ success: true, ...exportData });
      }

      default:
        return jsonResponse_({ success: false, message: "Invalid action parameter: " + action });
    }
  } catch (err) {
    return jsonResponse_({ success: false, error: "UNAUTHORIZED", message: err.message || "Server error." });
  }
}

/**
 * Standard JSON response helper for REST endpoints.
 */
function jsonResponse_(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Secret key management for HMAC-SHA256 session tokens.
 */
function getSecretKey_() {
  const props = PropertiesService.getScriptProperties();
  let secret = props.getProperty("AUTH_SECRET");
  if (!secret) {
    secret = "APCNF_RBAC_SECRET_" + Utilities.getUuid();
    props.setProperty("AUTH_SECRET", secret);
  }
  return secret;
}

/**
 * Generates an HMAC-SHA256 signed session token.
 */
function generateToken_(userId, role, name, payloadExtra) {
  const header = Utilities.base64EncodeWebSafe(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const exp = Math.floor(Date.now() / 1000) + (role === CONFIG.ROLES.ADMIN ? 86400 : 2592000); // 24h admin, 30d cadre
  const payloadData = Object.assign({
    sub: userId,
    role: role,
    name: name,
    exp: exp,
    iat: Math.floor(Date.now() / 1000)
  }, payloadExtra || {});
  const payload = Utilities.base64EncodeWebSafe(JSON.stringify(payloadData));
  const signatureBytes = Utilities.computeHmacSha256Signature(header + "." + payload, getSecretKey_());
  const signature = Utilities.base64EncodeWebSafe(signatureBytes);
  return header + "." + payload + "." + signature;
}

/**
 * Verifies an HMAC-SHA256 session token and checks required role.
 */
function verifyToken_(token, requiredRole) {
  if (!token || typeof token !== "string") {
    throw new Error("Missing authentication token. Authorization required.");
  }
  const parts = token.split(".");
  if (parts.length !== 3) {
    throw new Error("Invalid token format.");
  }
  const expectedSigBytes = Utilities.computeHmacSha256Signature(parts[0] + "." + parts[1], getSecretKey_());
  const expectedSig = Utilities.base64EncodeWebSafe(expectedSigBytes);
  if (expectedSig !== parts[2]) {
    throw new Error("Invalid token signature. Access denied.");
  }
  const payloadStr = Utilities.newBlob(Utilities.base64DecodeWebSafe(parts[1])).getDataAsString();
  const payload = JSON.parse(payloadStr);
  const now = Math.floor(Date.now() / 1000);
  if (payload.exp && payload.exp < now) {
    throw new Error("Session token has expired. Please log in again.");
  }
  if (requiredRole && payload.role !== requiredRole) {
    throw new Error("Access denied. Insufficient permissions. Required role: " + requiredRole);
  }
  return payload;
}

/**
 * SHA-256 password hashing with salt.
 */
function hashPassword_(password, salt) {
  const raw = String(password) + String(salt);
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, raw, Utilities.Charset.UTF_8);
  return digest.map(b => (b < 0 ? b + 256 : b).toString(16).padStart(2, "0")).join("");
}

/**
 * Authenticates admin against Admin_Users sheet.
 */
function authenticateAdmin_(username, password) {
  const ss = SpreadsheetApp.getActive();
  const sheet = ss.getSheetByName(CONFIG.SHEETS.ADMINS);
  if (!sheet) return null;

  const rows = sheet.getDataRange().getValues();
  const cleanUser = String(username).trim().toLowerCase();

  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    const rowUser = String(row[0] || "").trim().toLowerCase();
    const rowHash = String(row[1] || "").trim();
    const rowSalt = String(row[2] || "").trim();
    const rowName = String(row[3] || "").trim();
    const rowRole = String(row[4] || "ADMIN").trim();
    const rowStatus = String(row[5] || "Active").trim();

    if (rowUser === cleanUser && String(rowStatus).toLowerCase() === "active") {
      const computedHash = hashPassword_(password, rowSalt);
      if (computedHash === rowHash) {
        // Update LastLogin timestamp
        try {
          sheet.getRange(i + 1, 8).setValue(new Date());
        } catch (e) {}
        return {
          username: row[0],
          name: rowName,
          role: rowRole
        };
      }
    }
  }
  return null;
}

/**
 * Ensures required sheets and column headers exist with frozen top rows.
 * Seeds initial Admin_Users record if sheet is empty.
 */
function setupSheets_() {
  if (_sheetsInitialized) return;
  const ss = SpreadsheetApp.getActive();
  const headers = {
    Cadre_Master: ["Cadre ID", "Name", "Mobile", "Cadre Type", "District", "Mandal", "Village", "VO", "Status"],
    Attendance: ["Timestamp", "Date", "Time", "Cadre ID", "Name", "Cadre Type", "Activity", "Remarks", "Photo Link", "Latitude", "Longitude", "GPS Accuracy (m)"],
    Feedback: ["Timestamp", "Date", "Cadre ID", "Name", "Cadre Type", "Training/Meeting", "Trainer", "Content Rating", "Trainer Rating", "Usefulness Rating", "Overall Rating", "Suggestions"],
    Admin_Users: ["Username", "PasswordHash", "Salt", "Name", "Role", "Status", "CreatedAt", "LastLogin"]
  };

  Object.entries(headers).forEach(([sheetName, cols]) => {
    let sheet = ss.getSheetByName(sheetName);
    if (!sheet) sheet = ss.insertSheet(sheetName);
    if (sheet.getLastRow() === 0) {
      sheet.getRange(1, 1, 1, cols.length).setValues([cols]);
      sheet.setFrozenRows(1);

      // Seed initial default administrator account if Admin_Users newly created
      if (sheetName === CONFIG.SHEETS.ADMINS) {
        const defaultSalt = "apcnf_salt_" + Utilities.getUuid().slice(0, 8);
        const defaultHash = hashPassword_("Admin@APCNF2026", defaultSalt);
        sheet.appendRow([
          "admin@apcnf.gov.in",
          defaultHash,
          defaultSalt,
          "State Administrator",
          "ADMIN",
          "Active",
          new Date(),
          ""
        ]);
      }
    }
  });
  _sheetsInitialized = true;
}

/**
 * Normalizes dates into yyyy-MM-dd.
 */
function normalizeDate_(cellVal) {
  if (!cellVal) return "";
  if (cellVal instanceof Date) {
    return Utilities.formatDate(cellVal, CONFIG.TIMEZONE, "yyyy-MM-dd");
  }
  const s = String(cellVal).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
  const parsed = new Date(s);
  return isNaN(parsed.getTime()) ? s : Utilities.formatDate(parsed, CONFIG.TIMEZONE, "yyyy-MM-dd");
}

/**
 * Securely searches for a Cadre in Cadre_Master.
 */
function getCadre(id, mobile) {
  setupSheets_();
  const cleanId = String(id || "").trim().toUpperCase();
  const cleanMob = String(mobile || "").replace(/\D/g, "").slice(-10);

  if (!cleanId || cleanMob.length !== 10) {
    return null;
  }

  const sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEETS.CADRES);
  const rows = sheet.getDataRange().getValues();

  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    const rowId = String(row[0] || "").trim().toUpperCase();
    const rowMob = String(row[2] || "").replace(/\D/g, "").slice(-10);

    if (cleanId === rowId && cleanMob === rowMob) {
      return {
        cadreId: String(row[0] || "").trim(),
        name: String(row[1] || "").trim(),
        mobile: String(row[2] || "").trim(),
        cadreType: String(row[3] || "").trim(),
        district: String(row[4] || "").trim(),
        mandal: String(row[5] || "").trim(),
        village: String(row[6] || "").trim(),
        vo: String(row[7] || "").trim(),
        status: String(row[8] || "Active").trim()
      };
    }
  }
  return null;
}

/**
 * Searches for a Cadre in Cadre_Master strictly by verified Cadre ID.
 */
function getCadreById_(id) {
  setupSheets_();
  const cleanId = String(id || "").trim().toUpperCase();
  if (!cleanId) return null;

  const sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEETS.CADRES);
  const rows = sheet.getDataRange().getValues();

  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    const rowId = String(row[0] || "").trim().toUpperCase();

    if (cleanId === rowId) {
      return {
        cadreId: String(row[0] || "").trim(),
        name: String(row[1] || "").trim(),
        mobile: String(row[2] || "").trim(),
        cadreType: String(row[3] || "").trim(),
        district: String(row[4] || "").trim(),
        mandal: String(row[5] || "").trim(),
        village: String(row[6] || "").trim(),
        vo: String(row[7] || "").trim(),
        status: String(row[8] || "Active").trim()
      };
    }
  }
  return null;
}

/**
 * Validates cadre identity and active status before data operations.
 */
function validate_(data) {
  if (!data || !data.cadreId || !data.mobile) {
    throw new Error("Cadre ID and Mobile Number are required.");
  }
  const cadre = getCadre(data.cadreId, data.mobile);
  if (!cadre) throw new Error("Cadre identity verification failed.");
  if (String(cadre.status).toLowerCase() !== "active") throw new Error("Cadre is not active in master database.");
  if (!CONFIG.CADRE_TYPES.includes(String(cadre.cadreType))) throw new Error("Invalid Cadre type: " + cadre.cadreType);
  if (String(cadre.name).toLowerCase() !== String(data.name || "").trim().toLowerCase()) {
    throw new Error("Cadre name verification mismatch.");
  }
  return cadre;
}

/**
 * Retrieves or creates the Drive folder for storing attendance photos.
 */
function getPhotoFolder_() {
  const folders = DriveApp.getFoldersByName(CONFIG.PHOTO_FOLDER);
  if (folders.hasNext()) {
    return folders.next();
  }
  return DriveApp.createFolder(CONFIG.PHOTO_FOLDER);
}

/**
 * Decodes and saves an attendance photo to Google Drive.
 */
function savePhoto_(data) {
  if (!data.photoBase64) throw new Error("Attendance photo is required.");
  
  const rawBase64 = String(data.photoBase64).replace(/^data:image\/\w+;base64,/, "");
  const bytes = Utilities.base64Decode(rawBase64);
  const now = new Date();
  const timeTag = Utilities.formatDate(now, CONFIG.TIMEZONE, "yyyyMMdd_HHmmss");
  const fileName = (data.cadreId || "CADRE") + "_" + timeTag + ".jpg";
  
  const folder = getPhotoFolder_();
  const blob = Utilities.newBlob(bytes, "image/jpeg", fileName);
  const file = folder.createFile(blob);
  
  try {
    file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  } catch (e) {}
  
  return file.getUrl();
}

/**
 * Checks if a cadre has already submitted attendance for today.
 */
function checkDuplicateAttendance_(cadreId, todayDate, activity) {
  const sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEETS.ATTENDANCE);
  const rows = sheet.getDataRange().getValues();
  const cleanId = String(cadreId).trim().toUpperCase();

  for (let i = 1; i < rows.length; i++) {
    const rowDate = normalizeDate_(rows[i][1]);
    const rowId = String(rows[i][3] || "").trim().toUpperCase();
    const rowActivity = String(rows[i][6] || "").trim();

    if (rowId === cleanId && rowDate === todayDate && rowActivity === activity) {
      return true;
    }
  }
  return false;
}

/**
 * Saves attendance record with concurrency locking and duplicate protection.
 */
function saveAttendance(data) {
  setupSheets_();
  const cadre = validate_(data);

  if (!CONFIG.ACTIVITIES.includes(String(data.activity))) {
    throw new Error("Invalid activity selected. Choose 'Field Visit' or 'Attend Meeting'.");
  }

  const lat = parseFloat(data.latitude);
  const lon = parseFloat(data.longitude);
  if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    throw new Error("Valid GPS location is required.");
  }

  const now = new Date();
  const todayDate = Utilities.formatDate(now, CONFIG.TIMEZONE, "yyyy-MM-dd");
  const currentTime = Utilities.formatDate(now, CONFIG.TIMEZONE, "HH:mm:ss");

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) {
    throw new Error("Server is currently busy processing other submissions. Please retry shortly.");
  }

  try {
    if (checkDuplicateAttendance_(cadre.cadreId, todayDate, data.activity)) {
      throw new Error("Attendance for '" + data.activity + "' has already been recorded today (" + todayDate + ").");
    }

    const photoUrl = savePhoto_(data);
    const sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEETS.ATTENDANCE);

    sheet.appendRow([
      now,
      todayDate,
      currentTime,
      cadre.cadreId,
      cadre.name,
      cadre.cadreType,
      data.activity,
      data.remarks || "",
      photoUrl,
      lat,
      lon,
      data.accuracy || ""
    ]);

    return { ok: true, message: "Attendance for '" + data.activity + "' recorded successfully." };
  } finally {
    lock.releaseLock();
  }
}

/**
 * Saves training/meeting feedback with validation and concurrency locking.
 */
function saveFeedback(data) {
  setupSheets_();
  const cadre = validate_(data);

  const now = new Date();
  const todayDate = Utilities.formatDate(now, CONFIG.TIMEZONE, "yyyy-MM-dd");

  const parseRating = (val) => {
    const num = parseInt(val, 10);
    return isNaN(num) || num < 1 || num > 5 ? 5 : num;
  };

  const contentRating = parseRating(data.contentRating);
  const trainerRating = parseRating(data.trainerRating);
  const usefulnessRating = parseRating(data.usefulnessRating);
  const overallRating = parseRating(data.overallRating);

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) {
    throw new Error("Server is busy. Please retry shortly.");
  }

  try {
    const sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEETS.FEEDBACK);
    sheet.appendRow([
      now,
      todayDate,
      cadre.cadreId,
      cadre.name,
      cadre.cadreType,
      data.training || "General Training",
      data.trainer || "Resource Person",
      contentRating,
      trainerRating,
      usefulnessRating,
      overallRating,
      data.suggestions || ""
    ]);

    return { ok: true, message: "Feedback submitted successfully. Thank you!" };
  } finally {
    lock.releaseLock();
  }
}

/**
 * Calculates dashboard statistics for cadre profile view.
 */
function getDashboard(cadreId) {
  setupSheets_();
  const ss = SpreadsheetApp.getActive();
  const now = new Date();
  const todayStr = Utilities.formatDate(now, CONFIG.TIMEZONE, "yyyy-MM-dd");

  const attSheet = ss.getSheetByName(CONFIG.SHEETS.ATTENDANCE);
  const fbSheet = ss.getSheetByName(CONFIG.SHEETS.FEEDBACK);

  const attRows = attSheet.getDataRange().getValues();
  const fbRows = fbSheet.getDataRange().getValues();

  let fieldVisitsToday = 0;
  let meetingsToday = 0;
  let myFieldVisitDone = false;
  let myMeetingDone = false;

  const targetCadreId = cadreId ? String(cadreId).trim().toUpperCase() : null;

  for (let i = 1; i < attRows.length; i++) {
    const rDate = normalizeDate_(attRows[i][1]);
    if (rDate === todayStr) {
      const act = String(attRows[i][6] || "").trim();
      if (act === "Field Visit") fieldVisitsToday++;
      if (act === "Attend Meeting") meetingsToday++;

      if (targetCadreId && String(attRows[i][3] || "").trim().toUpperCase() === targetCadreId) {
        if (act === "Field Visit") myFieldVisitDone = true;
        if (act === "Attend Meeting") myMeetingDone = true;
      }
    }
  }

  return {
    today: todayStr,
    totalFieldVisits: fieldVisitsToday,
    totalMeetings: meetingsToday,
    totalFeedback: Math.max(0, fbRows.length - 1),
    myAttendance: {
      fieldVisitDone: myFieldVisitDone,
      meetingDone: myMeetingDone
    }
  };
}

/**
 * ADMIN DATA API: Returns overall aggregated metrics across all cadres.
 * Callable strictly by authenticated ADMIN role.
 */
function getAdminDashboardData_() {
  const ss = SpreadsheetApp.getActive();
  const now = new Date();
  const todayStr = Utilities.formatDate(now, CONFIG.TIMEZONE, "yyyy-MM-dd");

  const cadreRows = ss.getSheetByName(CONFIG.SHEETS.CADRES).getDataRange().getValues();
  const attRows = ss.getSheetByName(CONFIG.SHEETS.ATTENDANCE).getDataRange().getValues();
  const fbRows = ss.getSheetByName(CONFIG.SHEETS.FEEDBACK).getDataRange().getValues();

  let activeCadres = 0;
  const cadreTypes = { FMT: 0, ICRP: 0, "T-ICRP": 0 };
  for (let i = 1; i < cadreRows.length; i++) {
    if (String(cadreRows[i][8] || "Active").toLowerCase() === "active") activeCadres++;
    const t = String(cadreRows[i][3] || "").trim();
    if (cadreTypes[t] !== undefined) cadreTypes[t]++;
  }

  let fieldVisitsToday = 0;
  let meetingsToday = 0;
  const recentAttendance = [];

  for (let i = attRows.length - 1; i >= 1; i--) {
    const rDate = normalizeDate_(attRows[i][1]);
    const act = String(attRows[i][6] || "").trim();
    if (rDate === todayStr) {
      if (act === "Field Visit") fieldVisitsToday++;
      if (act === "Attend Meeting") meetingsToday++;
    }
    if (recentAttendance.length < 15) {
      recentAttendance.push({
        timestamp: attRows[i][0],
        date: rDate,
        time: String(attRows[i][2] || ""),
        cadreId: String(attRows[i][3] || ""),
        name: String(attRows[i][4] || ""),
        cadreType: String(attRows[i][5] || ""),
        activity: act,
        remarks: String(attRows[i][7] || ""),
        photoLink: String(attRows[i][8] || ""),
        latitude: attRows[i][9],
        longitude: attRows[i][10],
        accuracy: attRows[i][11]
      });
    }
  }

  let ratingSum = 0;
  for (let i = 1; i < fbRows.length; i++) {
    ratingSum += Number(fbRows[i][10] || 0); // Overall rating column
  }
  const fbCount = Math.max(0, fbRows.length - 1);
  const avgRating = fbCount > 0 ? Math.round((ratingSum / fbCount) * 10) / 10 : 0;

  return {
    today: todayStr,
    totalCadres: Math.max(0, cadreRows.length - 1),
    activeCadres: activeCadres,
    cadreTypes: cadreTypes,
    todayFieldVisits: fieldVisitsToday,
    todayMeetings: meetingsToday,
    totalFeedback: fbCount,
    averageRating: avgRating,
    recentAttendance: recentAttendance
  };
}

/**
 * ADMIN DATA API: Returns all records for administrative oversight.
 */
function getAdminAllData_() {
  const ss = SpreadsheetApp.getActive();
  const cadreRows = ss.getSheetByName(CONFIG.SHEETS.CADRES).getDataRange().getValues();
  const attRows = ss.getSheetByName(CONFIG.SHEETS.ATTENDANCE).getDataRange().getValues();
  const fbRows = ss.getSheetByName(CONFIG.SHEETS.FEEDBACK).getDataRange().getValues();

  const cadres = [];
  for (let i = 1; i < cadreRows.length; i++) {
    cadres.push({
      cadreId: cadreRows[i][0],
      name: cadreRows[i][1],
      mobile: cadreRows[i][2],
      cadreType: cadreRows[i][3],
      district: cadreRows[i][4],
      mandal: cadreRows[i][5],
      village: cadreRows[i][6],
      vo: cadreRows[i][7],
      status: cadreRows[i][8]
    });
  }

  return {
    cadres: cadres,
    totalAttendanceRecords: Math.max(0, attRows.length - 1),
    totalFeedbackRecords: Math.max(0, fbRows.length - 1)
  };
}

/**
 * ADMIN SEARCH & FILTER API: Retrieves attendance history with multi-field filtering.
 */
function getAdminAttendanceList_(payload) {
  const ss = SpreadsheetApp.getActive();
  const attRows = ss.getSheetByName(CONFIG.SHEETS.ATTENDANCE).getDataRange().getValues();
  const filterDate = payload.date && payload.date !== "ALL" ? String(payload.date).trim() : null;
  const filterActivity = payload.activity && payload.activity !== "ALL" ? String(payload.activity).trim() : null;
  const filterCadreType = payload.cadreType && payload.cadreType !== "ALL" ? String(payload.cadreType).trim().toUpperCase() : null;
  const filterQuery = payload.query ? String(payload.query).trim().toLowerCase() : null;
  const limit = Math.min(Math.max(Number(payload.limit) || 100, 1), 200);

  const results = [];
  for (let i = attRows.length - 1; i >= 1; i--) {
    const row = attRows[i];
    const rDate = normalizeDate_(row[1]);
    const rCadreId = String(row[3] || "").trim();
    const rName = String(row[4] || "").trim();
    const rCadreType = String(row[5] || "").trim().toUpperCase();
    const rActivity = String(row[6] || "").trim();
    const rRemarks = String(row[7] || "").trim();

    if (filterDate && rDate !== filterDate) continue;
    if (filterActivity && rActivity.toLowerCase() !== filterActivity.toLowerCase()) continue;
    if (filterCadreType && rCadreType !== filterCadreType) continue;

    if (filterQuery) {
      const match = rCadreId.toLowerCase().includes(filterQuery) ||
                    rName.toLowerCase().includes(filterQuery) ||
                    rRemarks.toLowerCase().includes(filterQuery);
      if (!match) continue;
    }

    results.push({
      timestamp: row[0],
      date: rDate,
      time: String(row[2] || ""),
      cadreId: rCadreId,
      name: rName,
      cadreType: rCadreType,
      activity: rActivity,
      remarks: rRemarks,
      photoLink: String(row[8] || ""),
      latitude: row[9],
      longitude: row[10],
      accuracy: row[11]
    });

    if (results.length >= limit) break;
  }
  return results;
}

/**
 * ADMIN SEARCH & FILTER API: Retrieves feedback submissions with multi-field filtering.
 */
function getAdminFeedbackList_(payload) {
  const ss = SpreadsheetApp.getActive();
  const fbRows = ss.getSheetByName(CONFIG.SHEETS.FEEDBACK).getDataRange().getValues();
  const filterCadreType = payload.cadreType && payload.cadreType !== "ALL" ? String(payload.cadreType).trim().toUpperCase() : null;
  const filterMinRating = payload.minRating && payload.minRating !== "ALL" ? Number(payload.minRating) : null;
  const filterQuery = payload.query ? String(payload.query).trim().toLowerCase() : null;
  const limit = Math.min(Math.max(Number(payload.limit) || 100, 1), 200);

  const results = [];
  for (let i = fbRows.length - 1; i >= 1; i--) {
    const row = fbRows[i];
    const rDate = normalizeDate_(row[1]);
    const rCadreId = String(row[2] || "").trim();
    const rName = String(row[3] || "").trim();
    const rCadreType = String(row[4] || "").trim().toUpperCase();
    const rTraining = String(row[5] || "").trim();
    const rTrainer = String(row[6] || "").trim();
    const rOverallRating = Number(row[10] || 0);
    const rSuggestions = String(row[11] || "").trim();

    if (filterCadreType && rCadreType !== filterCadreType) continue;
    if (filterMinRating !== null && rOverallRating < filterMinRating) continue;

    if (filterQuery) {
      const match = rCadreId.toLowerCase().includes(filterQuery) ||
                    rName.toLowerCase().includes(filterQuery) ||
                    rTraining.toLowerCase().includes(filterQuery) ||
                    rTrainer.toLowerCase().includes(filterQuery) ||
                    rSuggestions.toLowerCase().includes(filterQuery);
      if (!match) continue;
    }

    results.push({
      timestamp: row[0],
      date: rDate,
      cadreId: rCadreId,
      name: rName,
      cadreType: rCadreType,
      training: rTraining,
      trainer: rTrainer,
      contentRating: Number(row[7] || 0),
      trainerRating: Number(row[8] || 0),
      usefulnessRating: Number(row[9] || 0),
      overallRating: rOverallRating,
      suggestions: rSuggestions
    });

    if (results.length >= limit) break;
  }
  return results;
}

/**
 * ADMIN SEARCH & FILTER API: Retrieves master cadres directory with status and type filtering.
 */
function getAdminCadreList_(payload) {
  const ss = SpreadsheetApp.getActive();
  const cadreRows = ss.getSheetByName(CONFIG.SHEETS.CADRES).getDataRange().getValues();
  const filterCadreType = payload.cadreType && payload.cadreType !== "ALL" ? String(payload.cadreType).trim().toUpperCase() : null;
  const filterStatus = payload.status && payload.status !== "ALL" ? String(payload.status).trim().toLowerCase() : null;
  const filterQuery = payload.query ? String(payload.query).trim().toLowerCase() : null;

  const results = [];
  for (let i = 1; i < cadreRows.length; i++) {
    const row = cadreRows[i];
    const rCadreId = String(row[0] || "").trim();
    const rName = String(row[1] || "").trim();
    const rMobile = String(row[2] || "").trim();
    const rCadreType = String(row[3] || "").trim().toUpperCase();
    const rDistrict = String(row[4] || "").trim();
    const rMandal = String(row[5] || "").trim();
    const rVillage = String(row[6] || "").trim();
    const rVo = String(row[7] || "").trim();
    const rStatus = String(row[8] || "Active").trim();

    if (filterCadreType && rCadreType !== filterCadreType) continue;
    if (filterStatus && rStatus.toLowerCase() !== filterStatus) continue;

    if (filterQuery) {
      const match = rCadreId.toLowerCase().includes(filterQuery) ||
                    rName.toLowerCase().includes(filterQuery) ||
                    rMobile.includes(filterQuery) ||
                    rDistrict.toLowerCase().includes(filterQuery) ||
                    rMandal.toLowerCase().includes(filterQuery) ||
                    rVillage.toLowerCase().includes(filterQuery);
      if (!match) continue;
    }

    results.push({
      cadreId: rCadreId,
      name: rName,
      mobile: rMobile,
      cadreType: rCadreType,
      district: rDistrict,
      mandal: rMandal,
      village: rVillage,
      vo: rVo,
      status: rStatus
    });
  }
  return results;
}

/**
 * ADMIN EXPORT API: Exports cadre attendance records to CSV/Excel format based on Date From and To.
 */
function exportAdminAttendanceCsv_(payload) {
  const ss = SpreadsheetApp.getActive();
  const attRows = ss.getSheetByName(CONFIG.SHEETS.ATTENDANCE).getDataRange().getValues();
  
  const fromDate = payload.fromDate ? String(payload.fromDate).trim() : "2000-01-01";
  const toDate = payload.toDate ? String(payload.toDate).trim() : "2099-12-31";
  const filterActivity = payload.activity && payload.activity !== "ALL" ? String(payload.activity).trim().toLowerCase() : null;
  const filterCadreType = payload.cadreType && payload.cadreType !== "ALL" ? String(payload.cadreType).trim().toUpperCase() : null;

  const headers = [
    "Date", "Time", "Cadre ID", "Cadre Name", "Cadre Type", 
    "Activity", "Remarks", "Latitude", "Longitude", "Accuracy (m)", "Photo URL"
  ];

  const escapeCsv = (val) => {
    if (val === null || val === undefined) return '""';
    const s = String(val).replace(/"/g, '""');
    return '"' + s + '"';
  };

  const csvLines = [headers.map(escapeCsv).join(",")];
  const records = [];

  for (let i = 1; i < attRows.length; i++) {
    const row = attRows[i];
    const rDate = normalizeDate_(row[1]);
    const rTime = String(row[2] || "");
    const rCadreId = String(row[3] || "").trim();
    const rName = String(row[4] || "").trim();
    const rCadreType = String(row[5] || "").trim().toUpperCase();
    const rActivity = String(row[6] || "").trim();
    const rRemarks = String(row[7] || "").trim();
    const rPhoto = String(row[8] || "").trim();
    const rLat = row[9] !== undefined ? row[9] : "";
    const rLon = row[10] !== undefined ? row[10] : "";
    const rAcc = row[11] !== undefined ? row[11] : "";

    // Date range filter
    if (rDate < fromDate || rDate > toDate) continue;

    // Optional filters
    if (filterActivity && rActivity.toLowerCase() !== filterActivity) continue;
    if (filterCadreType && rCadreType !== filterCadreType) continue;

    csvLines.push([
      escapeCsv(rDate),
      escapeCsv(rTime),
      escapeCsv(rCadreId),
      escapeCsv(rName),
      escapeCsv(rCadreType),
      escapeCsv(rActivity),
      escapeCsv(rRemarks),
      escapeCsv(rLat),
      escapeCsv(rLon),
      escapeCsv(rAcc),
      escapeCsv(rPhoto)
    ].join(","));

    records.push({
      date: rDate,
      time: rTime,
      cadreId: rCadreId,
      name: rName,
      cadreType: rCadreType,
      activity: rActivity,
      remarks: rRemarks,
      latitude: rLat,
      longitude: rLon,
      accuracy: rAcc,
      photoLink: rPhoto
    });
  }

  const filename = "APCNF_Attendance_" + fromDate + "_to_" + toDate + ".csv";
  const sheetUrl = ss ? ss.getUrl() : "";

  return {
    filename: filename,
    fromDate: fromDate,
    toDate: toDate,
    count: records.length,
    sheetUrl: sheetUrl,
    csvContent: csvLines.join("\r\n"),
    data: records
  };
}


