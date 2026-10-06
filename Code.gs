/**
 * APCNF Cadre Attendance & Feedback App (v2.1)
 * Backend: Google Apps Script + Google Sheets + Google Drive
 * Supports both Web App client and Native Android App (via doPost REST API)
 * Organization: Andhra Pradesh Community Managed Natural Farming (RySS)
 */

const CONFIG = {
  APP_NAME: "APCNF Cadre Attendance & Feedback",
  VERSION: "2.1.0",
  TIMEZONE: "Asia/Kolkata",
  CADRE_TYPES: ["FMT", "ICRP", "T-ICRP"],
  ACTIVITIES: ["Field Visit", "Attend Meeting"],
  SHEETS: {
    CADRES: "Cadre_Master",
    ATTENDANCE: "Attendance",
    FEEDBACK: "Feedback"
  },
  PHOTO_FOLDER: "APCNF Cadre Attendance Photos"
};

let _sheetsInitialized = false;

/**
 * Web App entry point for web browsers.
 */
function doGet(e) {
  setupSheets_();
  
  // If query param action=status is passed, return JSON status
  if (e && e.parameter && e.parameter.action === "status") {
    return jsonResponse_({
      status: "online",
      appName: CONFIG.APP_NAME,
      version: CONFIG.VERSION,
      serverTime: Utilities.formatDate(new Date(), CONFIG.TIMEZONE, "yyyy-MM-dd HH:mm:ss")
    });
  }

  return HtmlService.createTemplateFromFile("Index")
    .evaluate()
    .setTitle(CONFIG.APP_NAME)
    .addMetaTag("viewport", "width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.DEFAULT);
}

/**
 * REST API entry point for Native Android App.
 * Expects JSON payload in postData.contents with an "action" field.
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
      case "login": {
        const cadre = getCadre(payload.cadreId, payload.mobile);
        if (!cadre) {
          return jsonResponse_({ success: false, message: "Cadre not found. Please verify Cadre ID and Mobile Number." });
        }
        if (String(cadre.status || "Active").toLowerCase() !== "active") {
          return jsonResponse_({ success: false, message: "Cadre status is currently inactive. Contact Mandal Incharge." });
        }
        return jsonResponse_({ success: true, message: "Login successful.", cadre: cadre });
      }

      case "saveAttendance": {
        const result = saveAttendance(payload);
        return jsonResponse_({ success: true, message: result.message, timestamp: new Date().toISOString() });
      }

      case "saveFeedback": {
        const result = saveFeedback(payload);
        return jsonResponse_({ success: true, message: result.message, timestamp: new Date().toISOString() });
      }

      case "getDashboard": {
        const dash = getDashboard(payload.cadreId);
        return jsonResponse_({ success: true, data: dash });
      }

      default:
        return jsonResponse_({ success: false, message: "Invalid action parameter: " + action });
    }
  } catch (err) {
    return jsonResponse_({ success: false, message: err.message || "An unexpected server error occurred." });
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
 * Ensures required sheets and column headers exist with frozen top rows.
 */
function setupSheets_() {
  if (_sheetsInitialized) return;
  const ss = SpreadsheetApp.getActive();
  const headers = {
    Cadre_Master: ["Cadre ID", "Name", "Mobile", "Cadre Type", "District", "Mandal", "Village", "VO", "Status"],
    Attendance: ["Timestamp", "Date", "Time", "Cadre ID", "Name", "Cadre Type", "Activity", "Remarks", "Photo Link", "Latitude", "Longitude", "GPS Accuracy (m)"],
    Feedback: ["Timestamp", "Date", "Cadre ID", "Name", "Cadre Type", "Training/Meeting", "Trainer", "Content Rating", "Trainer Rating", "Usefulness Rating", "Overall Rating", "Suggestions"]
  };

  Object.entries(headers).forEach(([sheetName, cols]) => {
    let sheet = ss.getSheetByName(sheetName);
    if (!sheet) sheet = ss.insertSheet(sheetName);
    if (sheet.getLastRow() === 0) {
      sheet.getRange(1, 1, 1, cols.length).setValues([cols]);
      sheet.setFrozenRows(1);
    }
  });
  _sheetsInitialized = true;
}

/**
 * Normalizes dates from Google Sheets (which may be Date objects or formatted strings) into yyyy-MM-dd.
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
 * Enforces strict matching of BOTH Cadre ID and registered Mobile Number (last 10 digits).
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
  } catch (e) {
    // Falls back gracefully if domain admin policies restrict public link sharing
  }
  
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

  // Acquire concurrency lock (up to 20 seconds wait)
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) {
    throw new Error("Server is currently busy processing other submissions. Please retry in a few moments.");
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
 * Calculates dashboard statistics for today with reliable date normalization.
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

  const feedbackTotal = Math.max(0, fbRows.length - 1);

  return {
    today: todayStr,
    totalFieldVisits: fieldVisitsToday,
    totalMeetings: meetingsToday,
    totalFeedback: feedbackTotal,
    myAttendance: {
      fieldVisitDone: myFieldVisitDone,
      meetingDone: myMeetingDone
    }
  };
}
