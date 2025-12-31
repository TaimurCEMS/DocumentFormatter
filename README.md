# Document Formatter Backend

Backend-first architecture for document formatting with real-time job status updates via Firestore.

## Architecture Overview

This is a **backend-first** system where the backend (Google Cloud Functions) is the single source of truth. FlutterFlow provides a thin UI layer that subscribes to Firestore document changes for real-time updates.

### Components

- **API Function** (`api`): HTTP endpoints for job submission and status retrieval
- **Worker Function** (`worker`): Background processor for document formatting
- **Firestore**: Real-time database for job state management
- **Pub/Sub**: Message queue for triggering worker processing
- **Cloud Storage**: File storage for input/output documents

### Flow

1. Client (FlutterFlow) calls `POST /api/process_document_stable` with `storage_path`
2. API creates `jobs/{doc_id}` document with `state: "QUEUED"` in Firestore
3. API publishes Pub/Sub message to trigger worker
4. Worker updates job to `PROCESSING`, processes document, then `COMPLETED`
5. Client subscribes to `jobs/{doc_id}` in Firestore for real-time updates
6. Client uses `download_url` from job document to download formatted file

## API Endpoints

### POST `/api/process_document_stable` (or `/process_document_stable`)

Submit a document for formatting.

**Request:**
```json
{
  "storage_path": "gs://bucket/path.docx",
  "style_prompt": "Formal Academic Style"  // optional
}
```

**Response:**
```json
{
  "doc_id": "uuid-here",
  "job_id": "uuid-here",  // alias
  "state": "QUEUED",
  "status": "QUEUED"  // alias
}
```

### GET `/api/v1/document_result` (or `/v1/document_result`)

Get job status and result (fallback endpoint for polling).

**Query Parameters:**
- `doc_id` (required): Job document ID

**Response:**
```json
{
  "doc_id": "uuid-here",
  "job_id": "uuid-here",  // alias
  "state": "COMPLETED",
  "status": "COMPLETED",  // alias
  "progress": 100,
  "display_message": "Completed",
  "formatted_text": "formatted text content...",
  "download_url": "https://firebasestorage.googleapis.com/...",
  "url": "https://firebasestorage.googleapis.com/...",  // alias
  "error": null,
  "owner_uid": "",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "version": "v1"
}
```

**States:**
- `QUEUED`: Job created, waiting for processing
- `PROCESSING`: Worker is formatting document
- `COMPLETED`: Document formatted successfully
- `FAILED`: Processing failed (check `error` field)

### GET `/api/v1/document_download` (or `/v1/document_download`)

Get download URL for completed document.

**Query Parameters:**
- `doc_id` (required): Job document ID

**Response:**
```json
{
  "download_url": "https://firebasestorage.googleapis.com/...",
  "url": "https://firebasestorage.googleapis.com/..."  // alias
}
```

## Firestore Schema

### Collection: `jobs`

**Document ID:** `{doc_id}` (UUID)

**Fields:**
```typescript
{
  doc_id: string              // Same as document ID
  job_id: string              // Alias (same as doc_id)
  storage_path: string         // Input file path (gs:// or Firebase URL)
  style_prompt: string         // Formatting style prompt
  state: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED"
  status: string               // Alias (always same as state)
  progress: number             // 0-100
  display_message: string       // User-friendly status message
  formatted_text: string | null // Formatted text (only when COMPLETED)
  download_url: string | null   // Firebase download token URL (only when COMPLETED)
  error: string | null          // Error message (only when FAILED)
  owner_uid: string             // Firebase Auth UID (empty string if unauthenticated)
  created_at: Timestamp         // Server timestamp
  updated_at: Timestamp         // Server timestamp
  version: "v1"                 // Schema version
}
```

**State Transitions:**
- `QUEUED` → `PROCESSING` → `COMPLETED`
- `QUEUED` → `PROCESSING` → `FAILED`

States never go backwards (idempotent processing).

## Storage Path Formats

The `storage_path` field accepts:

1. **Google Cloud Storage URL:**
   ```
   gs://bucket-name/path/to/file.docx
   ```

2. **Firebase Storage HTTP URL:**
   ```
   https://firebasestorage.googleapis.com/v0/b/bucket/o/path%2Fto%2Ffile.docx?alt=media&token=...
   ```

The worker automatically normalizes both formats to extract the object path.

## Output Files

Formatted documents are stored at:
```
outputs/{doc_id}_formatted.docx
```

Download URLs use **Firebase download tokens** (NOT signed URLs):
```
https://firebasestorage.googleapis.com/v0/b/{bucket}/o/{encoded_path}?alt=media&token={token}
```

The token is stored in blob metadata as `firebaseStorageDownloadTokens`.

## Deployment

### Prerequisites

- Google Cloud SDK installed and authenticated
- Project ID: `documentformatterapp`
- Region: `asia-southeast1`
- Runtime: `python313`

### Deploy API Function

**PowerShell:**
```powershell
.\scripts\deploy_api.ps1
```

**Bash:**
```bash
chmod +x scripts/deploy_api.sh
./scripts/deploy_api.sh
```

**Manual:**
```bash
gcloud functions deploy api \
  --gen2 \
  --runtime=python313 \
  --region=asia-southeast1 \
  --source=api \
  --entry-point=process_document_stable \
  --trigger-http \
  --allow-unauthenticated
```

### Deploy Worker Function

**PowerShell:**
```powershell
.\scripts\deploy_worker.ps1
```

**Bash:**
```bash
chmod +x scripts/deploy_worker.sh
./scripts/deploy_worker.sh
```

**Manual:**
```bash
gcloud functions deploy worker \
  --gen2 \
  --runtime=python313 \
  --region=asia-southeast1 \
  --source=worker \
  --entry-point=process_document_worker \
  --trigger-topic=document-processing-topic
```

## Testing

### PowerShell

```powershell
.\scripts\test_endpoints.ps1
```

### Manual Testing

**1. Submit a job:**
```powershell
$body = @{
    storage_path = "gs://bucket/input.docx"
    style_prompt = "Formal Academic Style"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://asia-southeast1-documentformatterapp.cloudfunctions.net/api/api/process_document_stable" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**2. Check job status:**
```powershell
$docId = "your-doc-id-here"
Invoke-RestMethod -Uri "https://asia-southeast1-documentformatterapp.cloudfunctions.net/api/api/v1/document_result?doc_id=$docId"
```

**3. Get download URL:**
```powershell
Invoke-RestMethod -Uri "https://asia-southeast1-documentformatterapp.cloudfunctions.net/api/api/v1/document_download?doc_id=$docId"
```

### cURL

**Submit job:**
```bash
curl -X POST https://asia-southeast1-documentformatterapp.cloudfunctions.net/api/api/process_document_stable \
  -H "Content-Type: application/json" \
  -d '{"storage_path": "gs://bucket/input.docx"}'
```

**Check status:**
```bash
curl "https://asia-southeast1-documentformatterapp.cloudfunctions.net/api/api/v1/document_result?doc_id=YOUR_DOC_ID"
```

## Troubleshooting

### "Invalid JSON" error on GET requests

**Fixed:** The manual router no longer parses JSON for GET requests. If you see this error, ensure you're using the latest deployed version.

### "Missing or invalid Authorization header"

**Fixed:** Authentication is optional. If Authorization header is missing, `owner_uid` is set to empty string.

### "you need a private key to sign credentials"

**Fixed:** All signed URL generation has been removed. The worker uses Firebase download token URLs only. If you see this error:

1. Check worker logs for `DOWNLOAD_URL=` output
2. Verify the URL is a Firebase token URL (not a signed URL)
3. Ensure `blob.metadata` and `blob.patch()` are called correctly

### Job stuck in QUEUED state

1. Check Pub/Sub topic `document-processing-topic` exists
2. Check worker function is deployed and active
3. Check worker logs for processing errors
4. Verify Firestore document was created correctly

### Job stuck in PROCESSING state

1. Check worker logs for errors
2. Verify input file exists at `storage_path`
3. Check worker has permissions to read from Storage
4. Verify worker has permissions to write to Firestore

### Download URL not working

1. Verify job is in `COMPLETED` state
2. Check `download_url` field in Firestore
3. Verify blob metadata contains `firebaseStorageDownloadTokens`
4. Test URL directly in browser

## Project Structure

```
DocumentFormatter/
├── api/
│   ├── main.py              # API function entrypoint
│   └── requirements.txt     # API dependencies
├── worker/
│   ├── main.py              # Worker function entrypoint
│   └── requirements.txt     # Worker dependencies
├── scripts/
│   ├── deploy_api.ps1       # Deploy API (PowerShell)
│   ├── deploy_api.sh        # Deploy API (Bash)
│   ├── deploy_worker.ps1    # Deploy Worker (PowerShell)
│   ├── deploy_worker.sh     # Deploy Worker (Bash)
│   └── test_endpoints.ps1   # Test all endpoints
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Response Aliases

For FlutterFlow compatibility, all responses include field aliases:

- `doc_id` + `job_id` (same value)
- `state` + `status` (same value)
- `download_url` + `url` (same value, when available)

Firestore documents also store both `state` and `status` fields (kept identical).

## Route Compatibility

All endpoints support both path variants:

- `/process_document_stable` OR `/api/process_document_stable`
- `/v1/document_result` OR `/api/v1/document_result`
- `/v1/document_download` OR `/api/v1/document_download`

## License

Private project - All rights reserved.
