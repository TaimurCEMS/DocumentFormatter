# FlutterFlow Implementation Guide

## Overview
This document describes how to implement the Document Formatter flow in FlutterFlow without using the `/v1/document_download` endpoint. Instead, use the `download_url` directly from `/v1/document_result`.

## Base URL
```
https://asia-southeast1-documentformatterapp.cloudfunctions.net/api
```

## API Endpoints

### 1. Process Document (Create Job)

**Endpoint:** `POST /process_document_stable`

**Request:**
- **Method:** POST
- **URL:** `https://asia-southeast1-documentformatterapp.cloudfunctions.net/api/process_document_stable`
- **Headers:**
  - `Content-Type: application/json`
- **Body (JSON):**
  ```json
  {
    "storage_path": "users/uploads/xxxxx.docx",
    "mode": "format_only",
    "style": "standard_clean"
  }
  ```

**Response:**
```json
{
  "doc_id": "uuid-string",
  "job_id": "uuid-string",
  "state": "QUEUED",
  "status": "QUEUED"
}
```

**FlutterFlow Implementation:**
1. Create an API Call action
2. Set method to POST
3. Set URL to: `https://asia-southeast1-documentformatterapp.cloudfunctions.net/api/process_document_stable`
4. Add header: `Content-Type: application/json`
5. Set body to JSON with:
   - `storage_path`: From Firebase Storage upload result (object path preferred, or full URL as fallback)
   - `mode`: `"format_only"` (hardcoded)
   - `style`: From dropdown selection (must be exactly `"standard_clean"` or `"compact_clean"`)
6. Store the returned `doc_id` in a page variable

### 2. Get Document Result (Polling)

**Endpoint:** `GET /v1/document_result?doc_id=...`

**Request:**
- **Method:** GET
- **URL:** `https://asia-southeast1-documentformatterapp.cloudfunctions.net/api/v1/document_result?doc_id={doc_id}`
- **Headers:** None required

**Response:**
```json
{
  "doc_id": "uuid-string",
  "job_id": "uuid-string",
  "state": "QUEUED|PROCESSING|COMPLETED|FAILED",
  "status": "QUEUED|PROCESSING|COMPLETED|FAILED",
  "progress": 0,
  "display_message": "string",
  "formatted_text": "string|null",
  "download_url": "string|null",
  "url": "string|null",
  "error": "string|null",
  "owner_uid": "string",
  "created_at": "RFC3339 string",
  "updated_at": "RFC3339 string",
  "version": "v1"
}
```

**FlutterFlow Implementation:**
1. Create an API Call action
2. Set method to GET
3. Set URL to: `https://asia-southeast1-documentformatterapp.cloudfunctions.net/api/v1/document_result?doc_id={doc_id}`
4. Use a Timer or Loop to poll every 2-3 seconds
5. Check `state` field:
   - If `"COMPLETED"`: Extract `download_url` and open it
   - If `"FAILED"`: Show error message from `error` field
   - If `"QUEUED"` or `"PROCESSING"`: Continue polling

## Complete Flow

### Step 1: Upload File to Firebase Storage
1. Use FlutterFlow's Firebase Storage upload action
2. Capture the upload result
3. Extract `storage_path`:
   - **Preferred:** Object path (e.g., `"users/uploads/xxxxx.docx"`)
   - **Fallback:** Full Firebase Storage download URL if object path is unavailable

### Step 2: Create Job
1. Create API Call to `POST /process_document_stable`
2. Set JSON body:
   ```json
   {
     "storage_path": "<from step 1>",
     "mode": "format_only",
     "style": "<dropdown value>"
   }
   ```
3. Style dropdown options (must be exact):
   - `"standard_clean"`
   - `"compact_clean"`
   - Default: `"standard_clean"`
4. Store returned `doc_id` in page variable

### Step 3: Poll for Result
1. Create API Call to `GET /v1/document_result?doc_id={doc_id}`
2. Set up polling (Timer widget or Loop):
   - Poll every 2-3 seconds
   - Stop when `state == "COMPLETED"` or `state == "FAILED"`
3. Check response `state`:
   - **COMPLETED:**
     - Extract `download_url` from response
     - Use FlutterFlow's "Launch URL" or "Open Link" action
     - Open `download_url` directly (no additional API call)
   - **FAILED:**
     - Extract `error` message from response
     - Display error to user
   - **QUEUED/PROCESSING:**
     - Show progress indicator
     - Continue polling

### Step 4: Open Download URL
When `state == "COMPLETED"`:
- Use FlutterFlow's built-in "Launch URL" action
- Set URL to the `download_url` value from the response
- This will open the formatted document directly in the browser/app

## Style Dropdown Configuration

**Required Values (exact match):**
- `standard_clean`
- `compact_clean`

**Default:** `standard_clean`

**Note:** The backend validates these values. Invalid style will return 400 error.

## Error Handling

### Common Errors:
1. **Missing storage_path:** 400 error - "Missing storage_path"
2. **Invalid style:** 400 error - "Invalid style. Allowed values: compact_clean, standard_clean"
3. **Job not found:** 404 error - Check doc_id is correct
4. **Processing failed:** Check `error` field in document_result response

## Important Notes

1. **No `/v1/document_download` endpoint needed** - Use `download_url` directly from `/v1/document_result`
2. **Content-Type header required** - Must be `application/json` for POST requests
3. **Base URL consistency** - Use the same base URL for all endpoints
4. **Polling frequency** - Recommended: 2-3 seconds between polls
5. **State values** - Always check `state` field (not `status`, though both exist for compatibility)

## Example FlutterFlow Actions Flow

```
1. Upload File → Firebase Storage
   ↓
2. Extract storage_path
   ↓
3. API Call: POST /process_document_stable
   Body: {
     "storage_path": "...",
     "mode": "format_only",
     "style": "standard_clean"
   }
   ↓
4. Store doc_id from response
   ↓
5. Start Timer (2-3 seconds)
   ↓
6. API Call: GET /v1/document_result?doc_id={doc_id}
   ↓
7. Check state:
   - COMPLETED → Launch URL (download_url)
   - FAILED → Show error
   - QUEUED/PROCESSING → Repeat from step 5
```

## Testing

Test with:
- Valid storage_path (Firebase Storage object path or URL)
- Both style values: `standard_clean` and `compact_clean`
- Verify polling stops on COMPLETED
- Verify download_url opens correctly
- Verify error handling for invalid inputs

