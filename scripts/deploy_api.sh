#!/bin/bash
# Deploy API Cloud Function
# Usage: ./scripts/deploy_api.sh

PROJECT_ID="documentformatterapp"
REGION="asia-southeast1"
FUNCTION_NAME="api"
RUNTIME="python313"
ENTRY_POINT="process_document_stable"
SOURCE_DIR="api"

echo "Deploying API function: $FUNCTION_NAME"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Runtime: $RUNTIME"

gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=$RUNTIME \
    --region=$REGION \
    --source=$SOURCE_DIR \
    --entry-point=$ENTRY_POINT \
    --trigger-http \
    --allow-unauthenticated \
    --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo ""
    echo "API deployment successful!"
    echo "Function URL: https://$REGION-$PROJECT_ID.cloudfunctions.net/$FUNCTION_NAME"
else
    echo ""
    echo "Deployment failed!"
    exit 1
fi

