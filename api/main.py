import functions_framework
from google.cloud import firestore
from google.cloud import pubsub_v1
from google.cloud import storage
import firebase_admin
from firebase_admin import auth, credentials
import uuid
import json
from datetime import datetime, timezone

# Lazy client initialization to avoid import-time credential errors
_db_client = None
_publisher_client = None
_storage_client = None
_firebase_app = None

PROJECT_ID = "documentformatterapp"
TOPIC_NAME = "document-processing-topic"
BUCKET_NAME = "documentformatterapp.firebasestorage.app"


def get_db():
    """Lazy initialization of Firestore client. Returns None if credentials are missing."""
    global _db_client
    if _db_client is None:
        try:
            _db_client = firestore.Client()
        except Exception as e:
            # Log but don't crash - allows server to start without credentials
            print(f"Warning: Could not initialize Firestore client: {str(e)}")
            return None
    return _db_client


def get_publisher():
    """Lazy initialization of Pub/Sub publisher client. Returns None if credentials are missing."""
    global _publisher_client
    if _publisher_client is None:
        try:
            _publisher_client = pubsub_v1.PublisherClient()
        except Exception as e:
            # Log but don't crash - allows server to start without credentials
            print(f"Warning: Could not initialize Pub/Sub publisher: {str(e)}")
            return None
    return _publisher_client


def get_topic_path():
    """Get the topic path, creating publisher if needed."""
    publisher = get_publisher()
    if publisher is None:
        return None
    return publisher.topic_path(PROJECT_ID, TOPIC_NAME)


def get_storage():
    """Lazy initialization of Cloud Storage client. Returns None if credentials are missing."""
    global _storage_client
    if _storage_client is None:
        try:
            _storage_client = storage.Client()
        except Exception as e:
            print(f"Warning: Could not initialize Storage client: {str(e)}")
            return None
    return _storage_client


def get_firebase_app():
    """Lazy initialization of Firebase Admin app. Returns None if credentials are missing."""
    global _firebase_app
    if _firebase_app is None:
        try:
            if not firebase_admin._apps:
                _firebase_app = firebase_admin.initialize_app()
            else:
                _firebase_app = firebase_admin.get_app()
        except Exception as e:
            print(f"Warning: Could not initialize Firebase Admin: {str(e)}")
            return None
    return _firebase_app


def verify_auth_token(request):
    """Verify Firebase Auth token from Authorization header. Returns (uid, error)."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None, "Missing or invalid Authorization header"
    
    token = auth_header.split('Bearer ')[1]
    if not token:
        return None, "Missing token"
    
    try:
        firebase_app = get_firebase_app()
        if firebase_app is None:
            return None, "Firebase Admin not configured"
        
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token.get('uid')
        if not uid:
            return None, "Token missing uid"
        return uid, None
    except Exception as e:
        return None, f"Invalid token: {str(e)}"


def verify_job_ownership(db, doc_id, owner_uid):
    """Verify that the user owns the job document. Returns (is_owner, error)."""
    try:
        doc_ref = db.collection('jobs').document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return False, "Job not found"
        
        data = doc.to_dict()
        doc_owner_uid = data.get('owner_uid')
        
        if doc_owner_uid != owner_uid:
            return False, "Unauthorized: You do not own this job"
        
        return True, None
    except Exception as e:
        return False, f"Error verifying ownership: {str(e)}"

def ensure_topic_exists():
    """Ensure the Pub/Sub topic exists, create if it doesn't."""
    publisher = get_publisher()
    if publisher is None:
        return  # Can't check topic without publisher
    
    topic_path = get_topic_path()
    if topic_path is None:
        return
    
    try:
        from google.api_core import exceptions
        try:
            publisher.get_topic(topic=topic_path)
            print(f"Topic {TOPIC_NAME} exists")
        except exceptions.NotFound:
            # Topic doesn't exist, try to create it
            try:
                publisher.create_topic(name=topic_path)
                print(f"Created topic {TOPIC_NAME}")
            except Exception as e:
                print(f"Error creating topic: {str(e)}")
                # Don't raise, just log - topic might be created by infrastructure
    except Exception as e:
        print(f"Error checking topic: {str(e)}")
        # Don't raise - continue anyway


def handle_process_document(request):
    """POST handler for process_document_stable endpoint."""
    headers = {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'}
    
    try:
        # Authentication is optional - if present, use it; otherwise set owner_uid to empty string
        owner_uid, _ = verify_auth_token(request)
        if owner_uid is None:
            owner_uid = ""  # Allow unauthenticated requests
        
        # Get Firestore client (lazy initialization)
        db = get_db()
        if db is None:
            return (json.dumps({"error": "Database service unavailable"}), 500, headers)
        
        # Parse JSON body safely (POST only)
        data = request.get_json(silent=True) or {}
        storage_path = data.get("storage_path") or data.get("storagePath")
        style_prompt = data.get("style_prompt") or data.get("stylePrompt") or "Formal Academic Style"
        
        # Parse mode and style with backward compatibility defaults
        mode = data.get("mode", "format_only")
        style = data.get("style", "standard_clean")
        
        # Validate style against allowed values
        allowed_styles = {"standard_clean", "compact_clean"}
        if style not in allowed_styles:
            return (json.dumps({"error": f"Invalid style. Allowed values: {', '.join(sorted(allowed_styles))}"}), 400, headers)
        
        if not storage_path:
            return (json.dumps({"error": "Missing storage_path"}), 400, headers)
        
        # Check if job already exists (idempotent creation)
        # If doc_id provided, use it; otherwise generate new
        doc_id = data.get('doc_id') or data.get('docId')
        if not doc_id:
            doc_id = str(uuid.uuid4())
        
        doc_ref = db.collection('jobs').document(doc_id)
        doc = doc_ref.get()
        
        if doc.exists:
            # Job already exists - return existing doc_id
            existing_data = doc.to_dict()
            # Only return if it belongs to the same user
            if existing_data.get('owner_uid') == owner_uid:
                state_value = existing_data.get('state', 'QUEUED')
                return (json.dumps({
                    "doc_id": doc_id,
                    "job_id": doc_id,  # Alias
                    "state": state_value,
                    "status": state_value  # Alias
                }), 200, headers)
            else:
                return (json.dumps({"error": "Job already exists with different owner"}), 409, headers)
        
        # Create new job document in jobs collection with new schema
        # Write both state and status for compatibility
        doc_ref.set({
            'doc_id': doc_id,
            'job_id': doc_id,  # Alias for compatibility
            'storage_path': storage_path,
            'style_prompt': style_prompt,
            'mode': mode,
            'style': style,
            'state': 'QUEUED',
            'status': 'QUEUED',  # Alias for compatibility (keep identical to state)
            'progress': 0,
            'display_message': '',  # Empty string as per requirement
            'formatted_text': None,
            'download_url': None,
            'error': None,
            'owner_uid': owner_uid,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'version': 'v1'
        })
        
        # Ensure topic exists before publishing
        try:
            ensure_topic_exists()
        except Exception as topic_error:
            print(f"Topic check failed: {str(topic_error)}")
            # Continue anyway, might still work
        
        # Get publisher and topic path (lazy initialization)
        publisher = get_publisher()
        topic_path = get_topic_path()
        
        if publisher is not None and topic_path is not None:
            message_data = {'doc_id': doc_id}
            message_bytes = json.dumps(message_data).encode('utf-8')
            
            try:
                future = publisher.publish(topic_path, message_bytes)
                message_id = future.result(timeout=10)  # Add timeout
                print(f"Published message {message_id} for doc_id {doc_id} to topic {TOPIC_NAME}")
            except Exception as pubsub_error:
                error_msg = f"Error publishing to Pub/Sub: {str(pubsub_error)}"
                print(error_msg)
                # Update job with error and set to FAILED
                doc_ref.update({
                    'state': 'FAILED',
                    'status': 'FAILED',  # Alias (keep identical)
                    'display_message': 'Failed to enqueue job',
                    'error': error_msg,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                return (json.dumps({"error": error_msg}), 500, headers)
        else:
            # Publisher unavailable - mark job as failed
            error_msg = "Pub/Sub publisher unavailable"
            print(f"Warning: {error_msg}, marking job {doc_id} as FAILED")
            doc_ref.update({
                'state': 'FAILED',
                'status': 'FAILED',  # Alias (keep identical)
                'display_message': 'Failed to enqueue job',
                'error': error_msg,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            return (json.dumps({"error": error_msg}), 500, headers)
        
        return (json.dumps({
            "doc_id": doc_id,
            "job_id": doc_id,  # Alias
            "state": "QUEUED",
            "status": "QUEUED"  # Alias
        }), 200, headers)
        
    except Exception as e:
        return (json.dumps({"error": str(e)}), 500, headers)


def handle_document_result(request):
    """GET handler for document_result endpoint."""
    headers = {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'}
    
    # For GET requests, ONLY read from query string (NEVER parse JSON)
    doc_id = request.args.get('doc_id')
    
    # If doc_id still missing, return error
    if not doc_id or doc_id.strip() == '':
        return (json.dumps({'error': 'missing doc_id'}), 400, headers)
    
    # Get Firestore client (lazy initialization)
    db = get_db()
    if db is None:
        return (json.dumps({'error': 'Database service unavailable'}), 500, headers)
    
    try:
        # Read from Firestore: jobs/{doc_id} (new schema)
        doc_ref = db.collection('jobs').document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return (json.dumps({'error': 'Job not found'}), 404, headers)
        
        # Document exists - extract data using new schema
        data = doc.to_dict()
        
        # Convert Firestore timestamps to ISO strings
        created_at = data.get('created_at')
        updated_at = data.get('updated_at')
        
        def convert_timestamp(ts):
            if not ts:
                return None
            try:
                if hasattr(ts, 'timestamp'):
                    dt = datetime.fromtimestamp(ts.timestamp(), tz=timezone.utc)
                    return dt.isoformat()
                elif isinstance(ts, str):
                    return ts
                elif isinstance(ts, datetime):
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    return ts.isoformat()
                else:
                    dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                    return dt.isoformat()
            except:
                return None
        
        # Get values with fallbacks
        state_value = data.get('state', data.get('status', 'FAILED'))  # Support both
        download_url_value = data.get('download_url')
        
        response_data = {
            'doc_id': doc_id,
            'job_id': doc_id,  # Alias for compatibility
            'state': state_value,
            'status': state_value,  # Alias for compatibility (keep identical)
            'progress': data.get('progress', 0),
            'display_message': data.get('display_message', ''),
            'formatted_text': data.get('formatted_text'),
            'download_url': download_url_value,
            'url': download_url_value,  # Alias for compatibility
            'error': data.get('error'),
            'owner_uid': data.get('owner_uid'),
            'created_at': convert_timestamp(created_at),
            'updated_at': convert_timestamp(updated_at),
            'version': data.get('version', 'v1')
        }
        
        # Return 200 with the job document
        return (json.dumps(response_data), 200, headers)
        
    except Exception as e:
        # Unexpected exception - return 500
        error_msg = str(e) if str(e) else 'Unexpected error'
        print(f"Error in document_result: {error_msg}")
        return (json.dumps({'error': error_msg}), 500, headers)


def handle_document_download(request):
    """GET handler for document_download endpoint."""
    headers = {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'}
    
    # For GET requests, ONLY read from query string (NEVER parse JSON)
    doc_id = request.args.get('doc_id')
    
    # If doc_id still missing, return error
    if not doc_id or doc_id.strip() == '':
        return (json.dumps({'error': 'missing doc_id'}), 400, headers)
    
    # Get Firestore client
    db = get_db()
    if db is None:
        return (json.dumps({'error': 'Database service unavailable'}), 500, headers)
    
    # Get job document
    doc_ref = db.collection('jobs').document(doc_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return (json.dumps({'error': 'Job not found'}), 404, headers)
    
    data = doc.to_dict()
    
    # Check if job is completed
    if data.get('state') != 'COMPLETED':
        return (json.dumps({'error': 'Document is not ready for download'}), 400, headers)
    
    # Get download_url from job document
    download_url = data.get('download_url')
    if not download_url:
        return (json.dumps({'error': 'Download URL not available'}), 400, headers)
    
    # Return JSON with both download_url and url aliases
    return (json.dumps({
        'download_url': download_url,
        'url': download_url  # Alias for compatibility
    }), 200, headers)


@functions_framework.http
def process_document_stable(request):
    """
    Manual router entrypoint - NO Flask app, NO test_request_context, NO global JSON parsing.
    Routes purely by request.path + request.method.
    """
    # Log request details
    query_string = request.query_string.decode('utf-8') if request.query_string else ''
    content_type = request.headers.get('Content-Type', '')
    print(f"REQ method={request.method} path={request.path} ct={content_type} qs={query_string}")
    
    # Handle OPTIONS requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    # Manual routing by path and method (NO JSON parsing until inside handlers)
    path = request.path
    
    # GET /v1/document_result OR /api/v1/document_result
    if request.method == 'GET' and (path == '/v1/document_result' or path == '/api/v1/document_result'):
        return handle_document_result(request)
    
    # GET /v1/document_download OR /api/v1/document_download
    if request.method == 'GET' and (path == '/v1/document_download' or path == '/api/v1/document_download'):
        return handle_document_download(request)
    
    # POST /process_document_stable OR /api/process_document_stable
    if request.method == 'POST' and (path == '/process_document_stable' or path == '/api/process_document_stable'):
        return handle_process_document(request)
    
    # 404 for unmatched routes
    headers = {'Content-Type': 'application/json'}
    return (json.dumps({'error': 'Not found'}), 404, headers)


# DEPRECATED: This endpoint is no longer used. Use /v1/document_result instead.
@functions_framework.http
def check_status(request):
    """DEPRECATED: Use /v1/document_result instead. This endpoint reads from old processing_jobs collection."""
    headers = {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'}
    return (json.dumps({"error": "This endpoint is deprecated. Use /v1/document_result instead."}), 410, headers)
