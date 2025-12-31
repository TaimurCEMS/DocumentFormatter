# Realtime Job Flow

## Overview

The Document Formatter uses Firestore as the single source of truth for realtime job status updates. Clients subscribe to Firestore document changes to receive push-based updates instead of polling.

## Firestore Collection: `jobs`

Each job is stored as a document in the `jobs` collection where the document ID equals the `docId` returned to the client.

### Document Schema

```typescript
{
  state: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED",
  progress: number,  // 0-100 (optional but recommended)
  display_message: string,
  formatted_text: string | null,  // Only when COMPLETED
  output: {
    storage_path: string,  // e.g. "outputs/{docId}/result.docx"
    mime: string
  } | null,  // Only when COMPLETED
  error: string | null,  // Only when FAILED
  owner_uid: string,  // Authenticated user ID
  created_at: Timestamp,
  updated_at: Timestamp,
  version: "v1"
}
```

## State Transitions

Jobs follow a strict state machine:

```
QUEUED → PROCESSING → COMPLETED
QUEUED → PROCESSING → FAILED
```

- States never go backwards
- Updates are idempotent (safe to retry)
- Terminal states: `COMPLETED`, `FAILED`

## Client Implementation (FlutterFlow/Flutter)

### 1. Subscribe to Job Document

```dart
import 'package:cloud_firestore/cloud_firestore.dart';

// Subscribe to job document changes
Stream<DocumentSnapshot> subscribeToJob(String docId) {
  return FirebaseFirestore.instance
    .collection('jobs')
    .doc(docId)
    .snapshots();
}

// Usage in widget
StreamBuilder<DocumentSnapshot>(
  stream: subscribeToJob(docId),
  builder: (context, snapshot) {
    if (!snapshot.hasData) {
      return CircularProgressIndicator();
    }
    
    final data = snapshot.data!.data() as Map<String, dynamic>;
    final state = data['state'] as String;
    final progress = data['progress'] as int? ?? 0;
    final displayMessage = data['display_message'] as String;
    
    // Update UI based on state
    switch (state) {
      case 'QUEUED':
        return Text('Queued: $displayMessage');
      case 'PROCESSING':
        return Column(
          children: [
            LinearProgressIndicator(value: progress / 100),
            Text('Processing: $displayMessage'),
          ],
        );
      case 'COMPLETED':
        return Column(
          children: [
            Text('Completed!'),
            ElevatedButton(
              onPressed: () => downloadDocument(docId),
              child: Text('Download'),
            ),
          ],
        );
      case 'FAILED':
        return Text('Failed: ${data['error']}');
    }
  },
)
```

### 2. Fields to Bind

**Always Available:**
- `state`: Current job state
- `progress`: Progress percentage (0-100)
- `display_message`: User-friendly status message
- `updated_at`: Last update timestamp

**When COMPLETED:**
- `formatted_text`: Formatted text content
- `output.storage_path`: Storage path for download
- `output.mime`: MIME type of output file

**When FAILED:**
- `error`: Error message

### 3. Download Document

When `state == "COMPLETED"`, call the download endpoint:

```dart
Future<void> downloadDocument(String docId) async {
  // Get Firebase Auth token
  final user = FirebaseAuth.instance.currentUser;
  final token = await user?.getIdToken();
  
  // Call download endpoint
  final response = await http.get(
    Uri.parse('https://your-api-url/v1/document_download?doc_id=$docId'),
    headers: {
      'Authorization': 'Bearer $token',
    },
  );
  
  if (response.statusCode == 200) {
    final data = json.decode(response.body);
    final downloadUrl = data['url'] as String;
    
    // Open URL in browser or download
    await launchUrl(Uri.parse(downloadUrl));
  }
}
```

## API Endpoints

### POST `/process_document_stable`

Creates a new job and returns `docId`.

**Request:**
```json
{
  "storage_path": "gs://bucket/path/to/file.docx",
  "style_prompt": "Formal Academic Style"
}
```

**Response:**
```json
{
  "doc_id": "uuid-here",
  "state": "QUEUED"
}
```

### GET `/v1/document_result?doc_id={docId}`

Fallback endpoint for manual refresh. Returns full job document.

**Headers:**
```
Authorization: Bearer {firebase_token}
```

**Response:**
```json
{
  "doc_id": "uuid-here",
  "state": "COMPLETED",
  "progress": 100,
  "display_message": "Completed",
  "formatted_text": "...",
  "output": {
    "storage_path": "outputs/{docId}/result.docx",
    "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  },
  "error": null,
  "owner_uid": "user-uid",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:05:00Z",
  "version": "v1"
}
```

### GET `/v1/document_download?doc_id={docId}`

Generates a short-lived signed URL for document download.

**Headers:**
```
Authorization: Bearer {firebase_token}
```

**Response:**
```json
{
  "url": "https://storage.googleapis.com/..."
}
```

**Note:** The signed URL expires in 10 minutes. FlutterFlow should open this URL immediately when the user taps Download.

## Firestore Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Jobs collection
    match /jobs/{docId} {
      // Only owner can read their job
      allow read: if request.auth != null && 
                     resource.data.owner_uid == request.auth.uid;
      
      // Only backend service account can write
      // (or validate writes server-side)
      allow write: if false;  // All writes go through backend
    }
  }
}
```

## Progress Tracking

The worker updates progress at key steps:

- **5%**: Job starts processing
- **20%**: Text extraction complete
- **50%**: AI formatting complete
- **75%**: Document generation complete
- **90%**: Upload to storage in progress
- **100%**: Job completed

## Error Handling

- If a job fails, `state` is set to `FAILED` and `error` contains a safe error message
- Clients should display the error message to users
- Jobs never transition backwards (idempotent updates)

## Best Practices

1. **Always subscribe** to the Firestore document for realtime updates
2. **Use `/v1/document_result`** only as a fallback for manual refresh
3. **Call `/v1/document_download`** when user taps Download (don't store URLs)
4. **Handle all states** in your UI (QUEUED, PROCESSING, COMPLETED, FAILED)
5. **Show progress** when `progress` field is available
6. **Display `display_message`** to provide user feedback

