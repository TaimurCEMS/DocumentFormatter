import functions_framework
from google.cloud import firestore
from google.cloud import storage
import requests
from docx import Document
from docx.shared import Pt, RGBColor
import io
import os
import json
import base64

db = firestore.Client()
storage_client = storage.Client()

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
BUCKET_NAME = "documentformatterapp.firebasestorage.app"


@functions_framework.cloud_event
def process_document_worker(cloud_event):
    try:
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        message_data = json.loads(pubsub_message)
        doc_id = message_data['doc_id']
        
        doc_ref = db.collection('processing_jobs').document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            print(f"Job {doc_id} not found")
            return
        
        data = doc.to_dict()
        storage_path = data['storage_path']
        style_prompt = data['style_prompt']
        
        doc_ref.update({'status': 'PROCESSING'})
        
        # Download document from Firebase Storage URL
        response = requests.get(storage_path)
        response.raise_for_status()
        
        # Extract text from DOCX
        doc_file = Document(io.BytesIO(response.content))
        extracted_text = '\n\n'.join([para.text for para in doc_file.paragraphs if para.text.strip()])
        
        # Format with OpenAI
        formatted_text = format_with_openai(extracted_text, style_prompt)
        
        # Generate formatted DOCX
        formatted_doc = Document()
        for line in formatted_text.split('\n'):
            if line.strip():
                p = formatted_doc.add_paragraph(line)
                for run in p.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
        
        # Save to Cloud Storage
        output_buffer = io.BytesIO()
        formatted_doc.save(output_buffer)
        output_buffer.seek(0)
        
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(f'users/formatted/{doc_id}_formatted.docx')
        blob.upload_from_file(output_buffer, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        blob.make_public()
        
        download_url = blob.public_url
        
        doc_ref.update({
            'status': 'COMPLETED',
            'formatted_text': formatted_text,
            'download_url': download_url,
            'error': ''
        })
        
        print(f"Job {doc_id} completed successfully")
        
    except Exception as e:
        print(f"Error processing job: {str(e)}")
        if 'doc_id' in locals():
            doc_ref.update({
                'status': 'FAILED',
                'error': str(e)
            })


def format_with_openai(text, style_prompt):
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': 'gpt-4o-mini',
        'messages': [
            {'role': 'system', 'content': f'You are a document formatter. Apply {style_prompt} formatting to the text. Return only the formatted text, no explanations.'},
            {'role': 'user', 'content': text}
        ],
        'temperature': 0.3
    }
    
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload )
    response.raise_for_status()
    
    return response.json()['choices'][0]['message']['content']
