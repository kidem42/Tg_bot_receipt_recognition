//pyHandler.gs

// General configuration
const GENERAL_CONFIG = {
  "insertAtTop": true,  // Set to true to insert new records at the top, false to insert at the bottom
  "use12HourFormat": true,  // Set to true for AM/PM format, false for 24-hour format
  "enableLogging": false,  // Set to true to enable logging to the Logs sheet, false to disable
  "enableCommentParsing": true  // Set to true to enable parsing triggers from comments
};

// Trigger words configuration
const TRIGGER_CONFIG = {
  "triggerMappings": {
    "MY": "Personal",
    "my": "Personal",
    "REP": "Company",
    "rep": "Company"
  },
  "separator": ", "  // Separator for multiple triggers in the Trigger column
};

/// Column order definition
const COLUMN_ORDER = [
  "RecordId",
  "Date",
  "Time",
  "Items",
  "Amount",
  "Currency",
  "Amount in USD",
  "Recipt",
  "Notes",
  "Type",
  "User ID",
  "User Name",
  "Timestamp"
];

// Column configuration (enable/disable columns)
const COLUMN_CONFIG = {
  "RecordId": true,  // Added RecordId column
  "Date": true,
  "Time": true,
  "Items": true,
  "Amount": true,
  "Currency": true,
  "Amount in USD": true,
  "Recipt": true,
  "Notes": true,
  "Type": true,  // Changed from Trigger to Type
  "User ID": true,
  "User Name": true,
  "Timestamp": true
};

// Columns to hide in the spreadsheet
const HIDDEN_COLUMNS = [
  "RecordId",  // Always hide RecordId column
  "Timestamp"    // Hide User ID column
  // Add more columns to hide as needed
];


// Column mapping from old to new names
const COLUMN_MAPPING = {
  "Telegram User ID": "User ID",
  "Telegram Username": "User Name",
  "Total Amount": "Amount",
  "Image URL": "Recipt"
};

// Helper function for logging
function logToSheet(message, type) {
  // If logging is disabled, do nothing
  if (!GENERAL_CONFIG.enableLogging) {
    return true;
  }
  
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var logSheet = ss.getSheetByName("Logs");
    
    if (!logSheet) {
      logSheet = ss.insertSheet("Logs");
      logSheet.appendRow(["Timestamp", "Type", "Message"]);
      logSheet.getRange(1, 1, 1, 3).setFontWeight("bold");
    }
    
    logSheet.appendRow([new Date().toISOString(), type || "INFO", message]);
    return true;
  } catch (e) {
    // If logging fails, we don't want to break the main functionality
    return false;
  }
}

// Function for handling HTTP requests
function doPost(e) {
  try {
    // Log incoming request
    logToSheet("Received request", "REQUEST");
    
    // Parse request body
    var params;
    try {
      params = JSON.parse(e.postData.contents);
      logToSheet("Request params: " + JSON.stringify(params), "INFO");
    } catch (error) {
      logToSheet("Failed to parse request body: " + error.toString(), "ERROR");
      return ContentService.createTextOutput(JSON.stringify({ 
        error: "Invalid request body",
        details: "Failed to parse JSON: " + error.toString()
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    var response = {};
    
    switch(params.action) {
      case 'createFolder':
        response = createFolder(params.parentFolderId, params.folderName);
        break;
      case 'uploadFile':
        response = uploadFile(params.folderId, params.fileName, params.fileContent, params.mimeType);
        break;
      case 'getFolderByName':
        response = getFolderByName(params.parentFolderId, params.folderName);
        break;
      case 'createExpenseRecord':
        response = createExpenseRecord(params.data);
        break;
      case 'updateReceiptNote':
        response = updateReceiptNote(params);
        break;
      case 'updateReceiptNoteByRecordId':
        response = updateReceiptNoteByRecordId(params);
        break;
      case 'test':
        // Simple test endpoint to verify API connectivity
        response = { 
          success: true, 
          message: "API connection successful",
          timestamp: new Date().toISOString()
        };
        break;
      default:
        logToSheet("Unknown action: " + params.action, "ERROR");
        response = { 
          error: "Unknown action",
          details: "The action '" + params.action + "' is not supported"
        };
    }
    
    // Log response
    logToSheet("Response: " + JSON.stringify(response), "RESPONSE");
    
    return ContentService.createTextOutput(JSON.stringify(response))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    // Catch any unexpected errors
    logToSheet("Unexpected error: " + error.toString(), "ERROR");
    return ContentService.createTextOutput(JSON.stringify({ 
      error: "Server error",
      details: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// Create folder
function createFolder(parentFolderId, folderName) {
  try {
    // Validate parameters
    if (!parentFolderId) {
      logToSheet("Missing parentFolderId in createFolder", "ERROR");
      return { 
        success: false, 
        error: "Missing parentFolderId parameter"
      };
    }
    
    if (!folderName) {
      logToSheet("Missing folderName in createFolder", "ERROR");
      return { 
        success: false, 
        error: "Missing folderName parameter"
      };
    }
    
    logToSheet("Creating folder: " + folderName + " in parent: " + parentFolderId, "INFO");
    
    var parentFolder;
    try {
      parentFolder = DriveApp.getFolderById(parentFolderId);
    } catch (e) {
      logToSheet("Invalid parentFolderId: " + parentFolderId + ", error: " + e.toString(), "ERROR");
      return { 
        success: false, 
        error: "Invalid parentFolderId",
        details: e.toString()
      };
    }
    
    var existingFolders = parentFolder.getFoldersByName(folderName);
    
    // If folder already exists, return it
    if (existingFolders.hasNext()) {
      var folder = existingFolders.next();
      var folderId = folder.getId();
      logToSheet("Folder already exists: " + folderName + ", ID: " + folderId, "INFO");
      return { 
        success: true, 
        folderId: folderId,
        message: "Folder already exists"
      };
    }
    
    // Create a new folder
    var newFolder = parentFolder.createFolder(folderName);
    var newFolderId = newFolder.getId();
    logToSheet("Folder created successfully: " + folderName + ", ID: " + newFolderId, "INFO");
    return { 
      success: true, 
      folderId: newFolderId,
      message: "Folder created successfully"
    };
  } catch (error) {
    logToSheet("Error in createFolder: " + error.toString(), "ERROR");
    return { 
      success: false, 
      error: "Failed to create folder",
      details: error.toString()
    };
  }
}

// Upload file
function uploadFile(folderId, fileName, fileContent, mimeType) {
  try {
    // Validate parameters
    if (!folderId) {
      logToSheet("Missing folderId in uploadFile", "ERROR");
      return { 
        success: false, 
        error: "Missing folderId parameter"
      };
    }
    
    if (!fileName) {
      logToSheet("Missing fileName in uploadFile", "ERROR");
      return { 
        success: false, 
        error: "Missing fileName parameter"
      };
    }
    
    if (!fileContent) {
      logToSheet("Missing fileContent in uploadFile", "ERROR");
      return { 
        success: false, 
        error: "Missing fileContent parameter"
      };
    }
    
    logToSheet("Uploading file: " + fileName + " to folder: " + folderId, "INFO");
    
    var folder;
    try {
      folder = DriveApp.getFolderById(folderId);
    } catch (e) {
      logToSheet("Invalid folderId: " + folderId + ", error: " + e.toString(), "ERROR");
      return { 
        success: false, 
        error: "Invalid folderId",
        details: e.toString()
      };
    }
    
    var decodedContent;
    try {
      decodedContent = Utilities.base64Decode(fileContent);
    } catch (e) {
      logToSheet("Failed to decode base64 content: " + e.toString(), "ERROR");
      return { 
        success: false, 
        error: "Invalid base64 content",
        details: e.toString()
      };
    }
    
    var blob = Utilities.newBlob(decodedContent, mimeType || "application/octet-stream", fileName);
    var file = folder.createFile(blob);
    var fileId = file.getId();
    
    logToSheet("File uploaded successfully: " + fileName + ", ID: " + fileId, "INFO");
    return { 
      success: true, 
      fileId: fileId,
      message: "File uploaded successfully"
    };
  } catch (error) {
    logToSheet("Error in uploadFile: " + error.toString(), "ERROR");
    return { 
      success: false, 
      error: "Failed to upload file",
      details: error.toString()
    };
  }
}

// Find folder by name
function getFolderByName(parentFolderId, folderName) {
  try {
    // Validate parameters
    if (!parentFolderId) {
      logToSheet("Missing parentFolderId in getFolderByName", "ERROR");
      return { 
        found: false, 
        error: "Missing parentFolderId parameter"
      };
    }
    
    if (!folderName) {
      logToSheet("Missing folderName in getFolderByName", "ERROR");
      return { 
        found: false, 
        error: "Missing folderName parameter"
      };
    }
    
    logToSheet("Searching for folder: " + folderName + " in parent: " + parentFolderId, "INFO");
    
    var parentFolder;
    try {
      parentFolder = DriveApp.getFolderById(parentFolderId);
    } catch (e) {
      logToSheet("Invalid parentFolderId: " + parentFolderId + ", error: " + e.toString(), "ERROR");
      return { 
        found: false, 
        error: "Invalid parentFolderId",
        details: e.toString()
      };
    }
    
    var folders = parentFolder.getFoldersByName(folderName);
    
    if (folders.hasNext()) {
      var folder = folders.next();
      var folderId = folder.getId();
      logToSheet("Folder found: " + folderName + ", ID: " + folderId, "INFO");
      return { 
        found: true, 
        folderId: folderId
      };
    } else {
      logToSheet("Folder not found: " + folderName, "INFO");
      return { 
        found: false
      };
    }
  } catch (error) {
    logToSheet("Error in getFolderByName: " + error.toString(), "ERROR");
    return { 
      found: false, 
      error: "Failed to search for folder",
      details: error.toString()
    };
  }
}


// Function to hide specified columns
function hideSpecifiedColumns(sheet) {
  // Loop through each column to hide
  for (const columnName of HIDDEN_COLUMNS) {
    const colIndex = findColumnByHeader(sheet, columnName);
    if (colIndex > 0) {
      sheet.hideColumns(colIndex);
      logToSheet(`Hidden column: ${columnName} (index: ${colIndex})`, "INFO");
    }
  }
}

// Find column index by header name
function findColumnByHeader(sheet, headerName) {
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  return headers.indexOf(headerName) + 1; // +1 because indices are 1-based in Sheets
}

// Create or get column by header name
function getOrCreateColumn(sheet, headerName) {
  let colIndex = findColumnByHeader(sheet, headerName);
  
  // If column doesn't exist, create it
  if (colIndex === 0) {
    // Add the new column at the end
    colIndex = sheet.getLastColumn() + 1;
    sheet.getRange(1, colIndex).setValue(headerName);
    sheet.getRange(1, colIndex).setFontWeight("bold");
  }
  
  return colIndex;
}

// Ensure required columns exist without recreating the sheet
function ensureColumnOrder(sheet) {
  // Get current headers
  const lastCol = sheet.getLastColumn();
  const currentHeaders = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  
  // Create a map of header name to column index
  const headerMap = {};
  currentHeaders.forEach((header, index) => {
    if (header) {
      // Check if this is an old header name that needs to be updated
      if (COLUMN_MAPPING[header]) {
        headerMap[COLUMN_MAPPING[header]] = index + 1;
        // Update the header name in the sheet
        sheet.getRange(1, index + 1).setValue(COLUMN_MAPPING[header]);
      } else {
        headerMap[header] = index + 1;
      }
    }
  });
  
  // Check if all required columns exist
  let missingColumns = [];
  for (const header of COLUMN_ORDER) {
    if (!COLUMN_CONFIG[header]) continue; // Skip disabled columns
    
    const currentIndex = headerMap[header];
    if (!currentIndex) {
      // Column doesn't exist, add it to missing columns list
      missingColumns.push(header);
    }
  }
  
  // Add any missing columns at the end
  if (missingColumns.length > 0) {
    logToSheet(`Adding missing columns: ${missingColumns.join(", ")}`, "INFO");
    
    // Add each missing column
    for (const header of missingColumns) {
      const newColIndex = sheet.getLastColumn() + 1;
      sheet.getRange(1, newColIndex).setValue(header);
      sheet.getRange(1, newColIndex).setFontWeight("bold");
      
      // Update the header map
      headerMap[header] = newColIndex;
    }
  }
  
  // Return the same sheet with possibly added columns
  return sheet;
}

// Function to update receipt note
function updateReceiptNote(params) {
  try {
    // Validate parameters
    if (!params.rowId) {
      return { 
        success: false, 
        error: "Missing rowId parameter"
      };
    }
    
    if (!params.note) {
      return { 
        success: false, 
        error: "Missing note parameter"
      };
    }
    
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Expenses");
    
    if (!sheet) {
      return { 
        success: false, 
        error: "Expenses sheet not found"
      };
    }
    
    // Find or create Notes column
    let notesColIndex = getOrCreateColumn(sheet, "Notes");
    
    // Update cell value
    sheet.getRange(params.rowId, notesColIndex).setValue(params.note);
    
    return { 
      success: true, 
      message: "Note updated successfully"
    };
  } catch (error) {
    return { 
      success: false, 
      error: "Failed to update note",
      details: error.toString()
    };
  }
}

// Function to parse triggers from comment
function parseTriggersFromComment(comment) {
  if (!GENERAL_CONFIG.enableCommentParsing) {
    return {
      triggers: "",
      cleanComment: comment
    };
  }

  const foundTriggers = new Set(); // Using Set to avoid duplicates
  let cleanComment = comment;

  // Find all trigger words in the comment and map them to their values
  Object.entries(TRIGGER_CONFIG.triggerMappings).forEach(([trigger, value]) => {
    const regex = new RegExp(`\\b${trigger}\\b`, 'g');
    if (regex.test(cleanComment)) {
      foundTriggers.add(value); // Add the mapped value instead of the trigger word
      cleanComment = cleanComment.replace(regex, '').trim();
    }
  });

  // Clean up multiple spaces that might have been created
  cleanComment = cleanComment.replace(/\s+/g, ' ').trim();

  return {
    triggers: Array.from(foundTriggers).join(TRIGGER_CONFIG.separator),
    cleanComment: cleanComment
  };
}

// Function to update receipt note by record ID
function updateReceiptNoteByRecordId(params) {
  try {
    // Validate parameters
    if (!params.recordId) {
      return { 
        success: false, 
        error: "Missing recordId parameter"
      };
    }
    
    if (!params.note) {
      return { 
        success: false, 
        error: "Missing note parameter"
      };
    }
    
    // Check if we're working with the correct spreadsheet
    if (params.spreadsheetId) {
      const currentSpreadsheetId = SpreadsheetApp.getActiveSpreadsheet().getId();
      if (params.spreadsheetId !== currentSpreadsheetId) {
        return { 
          success: false, 
          error: "Spreadsheet ID mismatch. This request should be sent to a different Google Script."
        };
      }
    }
    
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet;
    
    // If sheet ID is provided, try to find the sheet by ID
    if (params.sheetId) {
      const sheets = ss.getSheets();
      for (let i = 0; i < sheets.length; i++) {
        if (sheets[i].getSheetId().toString() === params.sheetId.toString()) {
          sheet = sheets[i];
          break;
        }
      }
      
      if (!sheet) {
        return { 
          success: false, 
          error: "Sheet with specified ID not found"
        };
      }
    } else {
      // Otherwise use the Expenses sheet
      sheet = ss.getSheetByName("Expenses");
      
      if (!sheet) {
        return { 
          success: false, 
          error: "Expenses sheet not found"
        };
      }
    }
    
    // Find RecordId, Notes, and Type columns
    let recordIdColIndex = findColumnByHeader(sheet, "RecordId");
    let notesColIndex = getOrCreateColumn(sheet, "Notes");
    let typeColIndex = getOrCreateColumn(sheet, "Type");
    
    if (recordIdColIndex === 0) {
      return { 
        success: false, 
        error: "RecordId column not found"
      };
    }
    
    // Get all values from RecordId column
    const lastRow = sheet.getLastRow();
    const recordIds = sheet.getRange(1, recordIdColIndex, lastRow, 1).getValues();
    
    // Find the row with the matching UUID
    let rowIndex = 0;
    for (let i = 0; i < recordIds.length; i++) {
      if (recordIds[i][0] === params.recordId) {
        rowIndex = i + 1; // +1 because indices in Sheets start at 1
        break;
      }
    }
    
    if (rowIndex === 0) {
      return { 
        success: false, 
        error: "Record with specified ID not found"
      };
    }
    
    // Parse the comment for triggers
    const { triggers, cleanComment } = parseTriggersFromComment(params.note);
    
    // Update the note and type columns
    sheet.getRange(rowIndex, notesColIndex).setValue(cleanComment);
    if (GENERAL_CONFIG.enableCommentParsing) {
      sheet.getRange(rowIndex, typeColIndex).setValue(triggers);
    }
    
    return { 
      success: true, 
      message: "Note and triggers updated successfully"
    };
  } catch (error) {
    return { 
      success: false, 
      error: "Failed to update note",
      details: error.toString()
    };
  }
}

// Create expense record in spreadsheet
function createExpenseRecord(data) {
  try {
    // Validate parameters
    if (!data) {
      logToSheet("Missing data in createExpenseRecord", "ERROR");
      return { 
        success: false, 
        error: "Missing data parameter"
      };
    }
    
    logToSheet("Creating expense record: " + JSON.stringify(data), "INFO");
    
    // Get the current spreadsheet to which the script is attached
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet;
    
    // Find or create "Expenses" sheet
    try {
      sheet = ss.getSheetByName("Expenses");
      if (!sheet) {
        // Create a new sheet if it doesn't exist
        sheet = ss.insertSheet("Expenses");
        
        // Add headers based on the enabled columns in the configuration
        const headers = COLUMN_ORDER.filter(header => COLUMN_CONFIG[header]);
        sheet.appendRow(headers);
        
        // Format headers
        sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold");
        
        // Hide specified columns
        hideSpecifiedColumns(sheet);
        
        logToSheet("Created new Expenses sheet", "INFO");
      } else {
        // Only ensure required columns exist, don't reorder or recreate the sheet
        sheet = ensureColumnOrder(sheet);
        
        // Hide specified columns
        hideSpecifiedColumns(sheet);
      }
    } catch (e) {
      logToSheet("Failed to access or create Expenses sheet: " + e.toString(), "ERROR");
      return { 
        success: false, 
        error: "Failed to access or create Expenses sheet",
        details: e.toString()
      };
    }
    
    // Get current timestamp
    var timestamp = new Date();
    
    // Generate UUID for the record
    const recordId = Utilities.getUuid();
    
    // Get spreadsheet and sheet IDs
    const spreadsheetId = SpreadsheetApp.getActiveSpreadsheet().getId();
    const sheetId = sheet.getSheetId();
    
    // Prepare row data based on enabled columns
    var rowData = {};
    
    // Add RecordId
    rowData["RecordId"] = recordId;
    
    // Map the data to the new column names
    if (COLUMN_CONFIG["User ID"]) rowData["User ID"] = data.telegram_user_id;
    if (COLUMN_CONFIG["User Name"]) rowData["User Name"] = data.telegram_username;
    if (COLUMN_CONFIG["Amount"]) rowData["Amount"] = data.total_amount;
    if (COLUMN_CONFIG["Currency"]) rowData["Currency"] = data.currency;
    if (COLUMN_CONFIG["Date"]) rowData["Date"] = data.date;
    if (COLUMN_CONFIG["Time"]) rowData["Time"] = data.time;
    if (COLUMN_CONFIG["Items"]) rowData["Items"] = data.items;
    if (COLUMN_CONFIG["Recipt"]) rowData["Recipt"] = data.image_url;
    if (COLUMN_CONFIG["Timestamp"]) rowData["Timestamp"] = timestamp;
    if (COLUMN_CONFIG["Notes"]) rowData["Notes"] = "";  // Initialize empty notes
    if (COLUMN_CONFIG["Type"]) rowData["Type"] = "";  // Initialize empty type

    // Create a new row
    var newRow = [];
    
    // Add values in the correct order
    for (const header of COLUMN_ORDER) {
      if (COLUMN_CONFIG[header]) {
        // Get or create the column
        getOrCreateColumn(sheet, header);
        
        // Add the value to the row (or empty string if not available)
        newRow.push(rowData[header] || "");
      }
    }
    
    // Insert the row at the top or bottom based on configuration
    if (GENERAL_CONFIG.insertAtTop) {
      // Insert after the header row
      sheet.insertRowAfter(1);
      
      // Get all column headers to preserve custom columns
      const allHeaders = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
      
      // Create a row with values for all columns
      const fullRowData = [];
      for (let i = 0; i < allHeaders.length; i++) {
        const header = allHeaders[i];
        if (!header) {
          fullRowData.push(""); // Empty cell for empty header
          continue;
        }
        
        // Check if this is a standard column we have data for
        let value = "";
        if (header === "RecordId") {
          value = recordId;
        } else if (header === "User ID") {
          value = data.telegram_user_id;
        } else if (header === "User Name") {
          value = data.telegram_username;
        } else if (header === "Amount") {
          value = data.total_amount;
        } else if (header === "Currency") {
          value = data.currency;
        } else if (header === "Date") {
          value = data.date;
        } else if (header === "Time") {
          value = data.time;
        } else if (header === "Items") {
          value = data.items;
        } else if (header === "Recipt") {
          value = data.image_url;
        } else if (header === "Timestamp") {
          value = timestamp;
        } else {
          // For custom columns, leave empty
          value = "";
        }
        
        fullRowData.push(value);
      }
      
      // Set the values for the entire row
      const newRowRange = sheet.getRange(2, 1, 1, fullRowData.length);
      newRowRange.setValues([fullRowData]);
      
      // Preserve existing formatting by copying from row 3 if it exists
      if (sheet.getLastRow() >= 3) {
        try {
          const formatSourceRange = sheet.getRange(3, 1, 1, fullRowData.length);
          formatSourceRange.copyFormatToRange(sheet, 1, fullRowData.length, 2, 2);
        } catch (e) {
          // If copying format fails, apply basic formatting
          newRowRange.setFontWeight("normal");
          
          // Apply formatting to date and time columns
          const dateColIndex = findColumnByHeader(sheet, "Date");
          const timeColIndex = findColumnByHeader(sheet, "Time");
          
          if (dateColIndex > 0) {
            sheet.getRange(2, dateColIndex).setNumberFormat("d mmm yyyy г.");
          }
          
          if (timeColIndex > 0) {
            if (GENERAL_CONFIG.use12HourFormat) {
              sheet.getRange(2, timeColIndex).setNumberFormat("h:mm AM/PM");
            } else {
              sheet.getRange(2, timeColIndex).setNumberFormat("HH:mm");
            }
          }
        }
      } else {
        // No existing rows to copy format from, apply basic formatting
        newRowRange.setFontWeight("normal");
        
        // Apply formatting to date and time columns
        const dateColIndex = findColumnByHeader(sheet, "Date");
        const timeColIndex = findColumnByHeader(sheet, "Time");
        
        if (dateColIndex > 0) {
          sheet.getRange(2, dateColIndex).setNumberFormat("d mmm yyyy г.");
        }
        
        if (timeColIndex > 0) {
          if (GENERAL_CONFIG.use12HourFormat) {
            sheet.getRange(2, timeColIndex).setNumberFormat("h:mm AM/PM");
          } else {
            sheet.getRange(2, timeColIndex).setNumberFormat("HH:mm");
          }
        }
      }
      
      // Return row ID 2 since we inserted at the top, along with recordId, spreadsheetId, and sheetId
      logToSheet("Expense record created successfully", "INFO");
      return { 
        success: true, 
        message: "Expense record created successfully",
        rowId: 2,
        recordId: recordId,
        spreadsheetId: spreadsheetId,
        sheetId: sheetId
      };
    } else {
      // For appending at the bottom, we need a similar approach to preserve custom columns
      // Get all column headers to preserve custom columns
      const allHeaders = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
      
      // Create a row with values for all columns
      const fullRowData = [];
      for (let i = 0; i < allHeaders.length; i++) {
        const header = allHeaders[i];
        if (!header) {
          fullRowData.push(""); // Empty cell for empty header
          continue;
        }
        
        // Check if this is a standard column we have data for
        let value = "";
        if (header === "RecordId") {
          value = recordId;
        } else if (header === "User ID") {
          value = data.telegram_user_id;
        } else if (header === "User Name") {
          value = data.telegram_username;
        } else if (header === "Amount") {
          value = data.total_amount;
        } else if (header === "Currency") {
          value = data.currency;
        } else if (header === "Date") {
          value = data.date;
        } else if (header === "Time") {
          value = data.time;
        } else if (header === "Items") {
          value = data.items;
        } else if (header === "Recipt") {
          value = data.image_url;
        } else if (header === "Timestamp") {
          value = timestamp;
        } else {
          // For custom columns, leave empty
          value = "";
        }
        
        fullRowData.push(value);
      }
      
      // Append the row
      sheet.appendRow(fullRowData);
      const newRowId = sheet.getLastRow();
      
      // Try to copy formatting from the previous row
      if (newRowId > 2) {
        try {
          const formatSourceRange = sheet.getRange(newRowId - 1, 1, 1, fullRowData.length);
          formatSourceRange.copyFormatToRange(sheet, 1, fullRowData.length, newRowId, newRowId);
        } catch (e) {
          // If copying format fails, apply basic formatting
          // Apply formatting to date and time columns
          const dateColIndex = findColumnByHeader(sheet, "Date");
          const timeColIndex = findColumnByHeader(sheet, "Time");
          
          if (dateColIndex > 0) {
            sheet.getRange(newRowId, dateColIndex).setNumberFormat("d mmm yyyy г.");
          }
          
          if (timeColIndex > 0) {
            if (GENERAL_CONFIG.use12HourFormat) {
              sheet.getRange(newRowId, timeColIndex).setNumberFormat("h:mm AM/PM");
            } else {
              sheet.getRange(newRowId, timeColIndex).setNumberFormat("HH:mm");
            }
          }
        }
      } else {
        // Apply basic formatting
        const dateColIndex = findColumnByHeader(sheet, "Date");
        const timeColIndex = findColumnByHeader(sheet, "Time");
        
        if (dateColIndex > 0) {
          sheet.getRange(newRowId, dateColIndex).setNumberFormat("d mmm yyyy г.");
        }
        
        if (timeColIndex > 0) {
          if (GENERAL_CONFIG.use12HourFormat) {
            sheet.getRange(newRowId, timeColIndex).setNumberFormat("h:mm AM/PM");
          } else {
            sheet.getRange(newRowId, timeColIndex).setNumberFormat("HH:mm");
          }
        }
      }
      
      logToSheet("Expense record created successfully", "INFO");
      return { 
        success: true, 
        message: "Expense record created successfully",
        rowId: newRowId,
        recordId: recordId,
        spreadsheetId: spreadsheetId,
        sheetId: sheetId
      };
    }
  } catch (error) {
    logToSheet("Error in createExpenseRecord: " + error.toString(), "ERROR");
    return { 
      success: false, 
      error: "Failed to create expense record",
      details: error.toString()
    };
  }
}
