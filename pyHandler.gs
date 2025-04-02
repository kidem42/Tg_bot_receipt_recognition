//pyHandler.gs

// Helper function to convert bytes to hex
function byteArrayToHex(bytes) {
  var hexString = '';
  for (var i = 0; i < bytes.length; i++) {
    var byteHex = (bytes[i] & 0xFF).toString(16);
    if (byteHex.length < 2) {
      byteHex = '0' + byteHex;
    }
    hexString += byteHex;
  }
  return hexString;
}

// Helper function for logging
function logToSheet(message, type) {
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
    // logToSheet("Received request: " + JSON.stringify(e.parameter), "REQUEST");
    
    // Security check - try to get headers from both URL parameters and request headers
    var headers = e.parameter;
    var apiKey = headers['X-API-Key'];
    var timestamp = headers['X-Timestamp'];
    var signature = headers['X-Signature'];
    
    // Log all parameters for debugging
    // logToSheet("All parameters: " + JSON.stringify(e.parameter), "DEBUG");
    
    // Check if headers are present
    if (!apiKey || !timestamp || !signature) {
      // logToSheet("Missing security headers in parameters, checking request headers", "INFO");
      
      // Try to get from request headers
      var requestHeaders = e.headers || {};
      apiKey = requestHeaders['X-API-Key'] || requestHeaders['x-api-key'];
      timestamp = requestHeaders['X-Timestamp'] || requestHeaders['x-timestamp'];
      signature = requestHeaders['X-Signature'] || requestHeaders['x-signature'];
      
      // If still missing, return error
      if (!apiKey || !timestamp || !signature) {
        // logToSheet("Missing security headers in both parameters and request headers", "ERROR");
        return ContentService.createTextOutput(JSON.stringify({ 
          error: "Missing security headers",
          details: "One or more required headers (X-API-Key, X-Timestamp, X-Signature) are missing"
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }
    
    // logToSheet("Using security headers - API Key: " + apiKey.substring(0, 5) + "..., Timestamp: " + timestamp + ", Signature: " + signature.substring(0, 10) + "...", "INFO");
    
    // API key check
    if (apiKey !== 'GOOGLE_SCRIPT_API_KEY') {
      // logToSheet("Invalid API key: " + apiKey, "ERROR");
      return ContentService.createTextOutput(JSON.stringify({ 
        error: "Invalid API key",
        details: "The provided API key does not match the expected value"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Request time check (not older than 5 minutes)
    var currentTime = Math.floor(Date.now() / 1000);
    if (currentTime - timestamp > 300) {
      // logToSheet("Request expired: current=" + currentTime + ", request=" + timestamp, "ERROR");
      return ContentService.createTextOutput(JSON.stringify({ 
        error: "Request expired",
        details: "The request timestamp is more than 5 minutes old"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Signature verification
    var expectedSignature = Utilities.computeDigest(
      Utilities.DigestAlgorithm.SHA_256,
      apiKey + timestamp
    );
    var expectedSignatureHex = byteArrayToHex(expectedSignature);
    
    if (signature !== expectedSignatureHex) {
      // logToSheet("Invalid signature: expected=" + expectedSignatureHex + ", received=" + signature, "ERROR");
      return ContentService.createTextOutput(JSON.stringify({ 
        error: "Invalid signature",
        details: "The provided signature does not match the expected value"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Log successful authentication
    // logToSheet("Authentication successful", "INFO");
  
    // Parse request body
    var params;
    try {
      params = JSON.parse(e.postData.contents);
      // logToSheet("Request params: " + JSON.stringify(params), "INFO");
    } catch (error) {
      // logToSheet("Failed to parse request body: " + error.toString(), "ERROR");
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
      case 'test':
        // Simple test endpoint to verify API connectivity
        response = { 
          success: true, 
          message: "API connection successful",
          timestamp: new Date().toISOString()
        };
        break;
      default:
        // logToSheet("Unknown action: " + params.action, "ERROR");
        response = { 
          error: "Unknown action",
          details: "The action '" + params.action + "' is not supported"
        };
    }
    
    // Log response
    // logToSheet("Response: " + JSON.stringify(response), "RESPONSE");
    
    return ContentService.createTextOutput(JSON.stringify(response))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    // Catch any unexpected errors
    // logToSheet("Unexpected error: " + error.toString(), "ERROR");
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
      // logToSheet("Missing parentFolderId in createFolder", "ERROR");
      return { 
        success: false, 
        error: "Missing parentFolderId parameter"
      };
    }
    
    if (!folderName) {
      // logToSheet("Missing folderName in createFolder", "ERROR");
      return { 
        success: false, 
        error: "Missing folderName parameter"
      };
    }
    
    // logToSheet("Creating folder: " + folderName + " in parent: " + parentFolderId, "INFO");
    
    var parentFolder;
    try {
      parentFolder = DriveApp.getFolderById(parentFolderId);
    } catch (e) {
      // logToSheet("Invalid parentFolderId: " + parentFolderId + ", error: " + e.toString(), "ERROR");
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
      // logToSheet("Folder already exists: " + folderName + ", ID: " + folderId, "INFO");
      return { 
        success: true, 
        folderId: folderId,
        message: "Folder already exists"
      };
    }
    
    // Create a new folder
    var newFolder = parentFolder.createFolder(folderName);
    var newFolderId = newFolder.getId();
    // logToSheet("Folder created successfully: " + folderName + ", ID: " + newFolderId, "INFO");
    return { 
      success: true, 
      folderId: newFolderId,
      message: "Folder created successfully"
    };
  } catch (error) {
    // logToSheet("Error in createFolder: " + error.toString(), "ERROR");
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
      // logToSheet("Missing folderId in uploadFile", "ERROR");
      return { 
        success: false, 
        error: "Missing folderId parameter"
      };
    }
    
    if (!fileName) {
      // logToSheet("Missing fileName in uploadFile", "ERROR");
      return { 
        success: false, 
        error: "Missing fileName parameter"
      };
    }
    
    if (!fileContent) {
      // logToSheet("Missing fileContent in uploadFile", "ERROR");
      return { 
        success: false, 
        error: "Missing fileContent parameter"
      };
    }
    
    // logToSheet("Uploading file: " + fileName + " to folder: " + folderId, "INFO");
    
    var folder;
    try {
      folder = DriveApp.getFolderById(folderId);
    } catch (e) {
      // logToSheet("Invalid folderId: " + folderId + ", error: " + e.toString(), "ERROR");
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
      // logToSheet("Failed to decode base64 content: " + e.toString(), "ERROR");
      return { 
        success: false, 
        error: "Invalid base64 content",
        details: e.toString()
      };
    }
    
    var blob = Utilities.newBlob(decodedContent, mimeType || "application/octet-stream", fileName);
    var file = folder.createFile(blob);
    var fileId = file.getId();
    
    // logToSheet("File uploaded successfully: " + fileName + ", ID: " + fileId, "INFO");
    return { 
      success: true, 
      fileId: fileId,
      message: "File uploaded successfully"
    };
  } catch (error) {
    // logToSheet("Error in uploadFile: " + error.toString(), "ERROR");
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
      // logToSheet("Missing parentFolderId in getFolderByName", "ERROR");
      return { 
        found: false, 
        error: "Missing parentFolderId parameter"
      };
    }
    
    if (!folderName) {
      // logToSheet("Missing folderName in getFolderByName", "ERROR");
      return { 
        found: false, 
        error: "Missing folderName parameter"
      };
    }
    
    // logToSheet("Searching for folder: " + folderName + " in parent: " + parentFolderId, "INFO");
    
    var parentFolder;
    try {
      parentFolder = DriveApp.getFolderById(parentFolderId);
    } catch (e) {
      // logToSheet("Invalid parentFolderId: " + parentFolderId + ", error: " + e.toString(), "ERROR");
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
      // logToSheet("Folder found: " + folderName + ", ID: " + folderId, "INFO");
      return { 
        found: true, 
        folderId: folderId
      };
    } else {
      // logToSheet("Folder not found: " + folderName, "INFO");
      return { 
        found: false
      };
    }
  } catch (error) {
    // logToSheet("Error in getFolderByName: " + error.toString(), "ERROR");
    return { 
      found: false, 
      error: "Failed to search for folder",
      details: error.toString()
    };
  }
}

// Create expense record in spreadsheet
function createExpenseRecord(data) {
  try {
    // Validate parameters
    if (!data) {
      // logToSheet("Missing data in createExpenseRecord", "ERROR");
      return { 
        success: false, 
        error: "Missing data parameter"
      };
    }
    
    // logToSheet("Creating expense record: " + JSON.stringify(data), "INFO");
    
    // Get the current spreadsheet to which the script is attached
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet;
    
    // Find or create "Expenses" sheet
    try {
      sheet = ss.getSheetByName("Expenses");
      if (!sheet) {
        // Create a new sheet if it doesn't exist
        sheet = ss.insertSheet("Expenses");
        
        // Add headers
        sheet.appendRow([
          "ID", 
          "Telegram User ID", 
          "Telegram Username", 
          "Total Amount", 
          "Tax Amount", 
          "Currency", 
          "Date", 
          "Time", 
          "Items", 
          "Image URL", 
          "Timestamp"
        ]);
        
        // Format headers
        sheet.getRange(1, 1, 1, 11).setFontWeight("bold");
        // logToSheet("Created new Expenses sheet", "INFO");
      }
    } catch (e) {
      // logToSheet("Failed to access or create Expenses sheet: " + e.toString(), "ERROR");
      return { 
        success: false, 
        error: "Failed to access or create Expenses sheet",
        details: e.toString()
      };
    }
    
    // Generate unique ID for the record
    var recordId = Utilities.getUuid();
    
    // Get current timestamp
    var timestamp = new Date().toISOString();
    
    // Add data to the table
    sheet.appendRow([
      recordId,
      data.telegram_user_id,
      data.telegram_username,
      data.total_amount,
      data.tax_amount,
      data.currency,
      data.date,
      data.time,
      data.items,
      data.image_url,
      timestamp
    ]);
    
    // logToSheet("Expense record created successfully: " + recordId, "INFO");
    return { 
      success: true, 
      recordId: recordId,
      message: "Expense record created successfully"
    };
  } catch (error) {
    // logToSheet("Error in createExpenseRecord: " + error.toString(), "ERROR");
    return { 
      success: false, 
      error: "Failed to create expense record",
      details: error.toString()
    };
  }
}
