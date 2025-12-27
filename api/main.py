import functions_framework
from flask import jsonify
from google.cloud import firestore
from google.cloud import pubsub_v1
import uuid
import json

db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

PROJECT_ID = "documentformatterapp"
TOPIC_NAME = "document-processing-topic"
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_NAME)


@functions_framework.http
def process_document_stable(request ):
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {'Access-Control-Allow-Origin': '*'}
    
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return (jsonify({"error": "Invalid JSON"}), 400, headers)
        
        storage_path = request_json.get('storage_path')
        style_prompt = request_json.get('style_prompt', 'Formal Academic Style')
        
        if not storage_path:
            return (jsonify({"error": "Missing storage_path"}), 400, headers)
        
        doc_id = str(uuid.uuid4())
        
        doc_ref = db.collection('processing_jobs').document(doc_id)
        doc_ref.set({
            'doc_id': doc_id,
            'storage_path': storage_path,
            'style_prompt': style_prompt,
            'status': 'QUEUED',
            'formatted_text': '',
            'download_url': '',
            'created_at': firestore.SERVER_TIMESTAMP,
            'error': ''
        })
        
        message_data = {'doc_id': doc_id}
        message_bytes = json.dumps(message_data).encode('utf-8')
        future = publisher.publish(topic_path, message_bytes)
        future.result()
        
        return (jsonify({"doc_id": doc_id, "status": "QUEUED"}), 200, headers)
        
    except Exception as e:
        return (jsonify({"error": str(e)}), 500, headers)


@functions_framework.http
def check_status(request ):
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {'Access-Control-Allow-Origin': '*'}
    
    try:
        # Get path and handle both Cloud Run and Cloud Functions routing
        path = request.path
        
        # Remove function name prefix if present
        if '/check_status/' in path:
            doc_id = path.split('/check_status/')[-1]
        elif path.startswith('/'):
            doc_id = path[1:]  # Remove leading slash
        else:
            doc_id = path
            
        if not doc_id or doc_id == 'check_status':
            return (jsonify({"error": "Missing doc_id"}), 400, headers)
        
        doc_ref = db.collection('processing_jobs').document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return (jsonify({"error": "Job not found"}), 404, headers)
        
        data = doc.to_dict()
        
        return (jsonify({
            "doc_id": data.get('doc_id', ''),
            "status": data.get('status', ''),
            "formatted_text": data.get('formatted_text', ''),
            "download_url": data.get('download_url', ''),
            "error": data.get('error', '')
        }), 200, headers)
        
    except Exception as e:
        return (jsonify({"error": str(e)}), 500, headers)
