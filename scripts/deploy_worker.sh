#!/bin/bash
# Deploy Worker Cloud Function
# Usage: ./scripts/deploy_worker.sh

PROJECT_ID="documentformatterapp"
REGION="asia-southeast1"
FUNCTION_NAME="worker"
RUNTIME="python313"
ENTRY_POINT="process_document_worker"
SOURCE_DIR="worker"
TOPIC_NAME="document-processing-topic"

echo "Deploying Worker function: $FUNCTION_NAME"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Runtime: $RUNTIME"
echo "Topic: $TOPIC_NAME"

gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=$RUNTIME \
    --region=$REGION \
    --source=$SOURCE_DIR \
    --entry-point=$ENTRY_POINT \
    --trigger-topic=$TOPIC_NAME \
    --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo ""
    echo "Worker deployment successful!"
else
    echo ""
    echo "Deployment failed!"
    exit 1
fi

