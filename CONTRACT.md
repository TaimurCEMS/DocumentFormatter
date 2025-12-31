# DocumentFormatter V1 Contract (Locked) + Roadmap Appendix (Non-binding)

This document is the source of truth for the thin-frontend architecture.
FlutterFlow renders. Backend decides.

Two parts:
- Part A: V1 Contract (Locked). Breaking changes require /v2.
- Part B: Roadmap Appendix (Non-binding). No impact on V1 behavior.

---

## Part A: V1 Contract (Locked)

### A0. System Roles (Non-negotiable)

Frontend (FlutterFlow)
- Uploads file to Firebase Storage.
- Calls the backend start endpoint once.
- Subscribes to Firestore `jobs/{docId}` in realtime.
- Renders backend fields. No frontend state machine.

Backend (Cloud Functions)
- Owns state transitions and error semantics.
- Writes authoritative fields into Firestore.
- Exposes result and download endpoints as the source of truth.

---

### A1. Public Base URL (Locked)

All endpoint paths below are relative to this base:

BASE_URL:
https://asia-southeast1-documentformatterapp.cloudfunctions.net/api

Examples:
- POST {BASE_URL}/process_document_stable
- GET  {BASE_URL}/v1/document_result?doc_id=...
- GET  {BASE_URL}/v1/document_download?doc_id=...

---

### A2. Start Processing Endpoint (V1)

Method: POST  
Path: /process_document_stable  
Auth: None in V1

Request JSON:
{
  "storage_path": "string (required)",
  "style_prompt": "string (optional)"
}

Rules:
- storage_path is required.
- style_prompt defaults to a backend-selected default if missing/empty.
- Backend must create Firestore `jobs/{docId}` and publish the Pub/Sub job.

Response JSON (minimum required keys):
{
  "doc_id": "string",
  "job_id": "string",
  "state": "QUEUED",
  "status": "QUEUED"
}

Notes:
- `job_id` is an alias of `doc_id` in V1.
- `status` is an alias of `state` in V1.

---

### A3. Accepted storage_path Formats (V1)

V1 supports the following inputs:

1) Firebase Storage download URL:
https://firebasestorage.googleapis.com/v0/b/<bucket>/o/<encodedPath>?alt=media&token=<token>

2) GCS style URL:
gs://<bucket>/<path>

Implementation note:
- Backend may normalize internally, but must store the original storage_path in Firestore.

---

### A4. Firestore Schema (Locked)

Collection: jobs  
Document ID: {docId} returned from Start Processing

Canonical fields (must exist):
- doc_id: string (same as Document ID)
- state: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED"
- progress: integer (0 to 100)
- display_message: string
- created_at: Firestore timestamp
- updated_at: Firestore timestamp
- version: string (example: "v1")
- storage_path: string
- style_prompt: string (may be empty)

Compatibility aliases (must mirror canonical values):
- status: same value as state

COMPLETED requirements:
- download_url: string (non-empty)
- formatted_text: string or null (allowed to be null if you do not store it)

FAILED requirements:
- error: string (user-safe)

Invariants:
- COMPLETED implies download_url is non-null and error is null
- FAILED implies error is non-null and download_url is null

---

### A5. Result Endpoint (V1)

Method: GET  
Path: /v1/document_result  
Query: doc_id (required)  
Auth: None in V1

Behavior:
- Reads Firestore `jobs/{doc_id}`
- Returns a stable JSON shape
- Does not modify state
- Does not trigger processing

Response JSON (always these keys):
{
  "doc_id": "string",
  "job_id": "string",
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
  "version": "string"
}

Notes:
- `url` is an alias of `download_url`.
- `job_id` is an alias of `doc_id`.

HTTP statuses:
- 200: valid request, includes state (including FAILED processing outcomes)
- 400: missing/invalid doc_id
- 404: doc_id not found

---

### A6. Download Endpoint (V1)

Method: GET  
Path: /v1/document_download  
Query: doc_id (required)  
Auth: None in V1

Behavior:
- Reads Firestore `jobs/{doc_id}`
- If state != COMPLETED or download_url is empty, return 400

Response JSON:
{
  "download_url": "string"
}

---

### A7. URL Generation Rule (Locked)

Backend must not generate signed URLs.
download_url must be a Firebase token URL in this format:

https://firebasestorage.googleapis.com/v0/b/<bucket>/o/<encodedPath>?alt=media&token=<token>

Worker must set firebaseStorageDownloadTokens metadata on the output blob.

---

### A8. Frontend Rule (Locked)

Frontend must:
- Call Start Processing once
- Navigate with docId
- Listen in realtime on jobs/{docId}
- Show download button only when state/status is COMPLETED and download_url exists

Frontend must not:
- Write to jobs collection
- Implement state transitions
- Infer meanings from missing fields

---

### A9. Contract Freeze Rule

This is V1. Any breaking change requires new V2 endpoints (/v2/...).
No silent breaking changes.

---

## Part B: Roadmap Appendix (Non-binding)

B1. Add stage breakdown fields (non-breaking):
- stage: "DOWNLOADING|EXTRACTING|FORMATTING|GENERATING|UPLOADING|FINALIZING"
- progress_percentage: 0 to 100

B2. Auth and ownership (V2)
- Require Bearer token
- Enforce owner_uid
- Add document history endpoints

B3. Productization (V3)
- Templates library
- Versioning
- Workspaces
- Billing and quotas

