# Deploy Worker Cloud Function
# Usage: .\scripts\deploy_worker.ps1

$PROJECT_ID = "documentformatterapp"
$REGION = "asia-southeast1"
$FUNCTION_NAME = "worker"
$RUNTIME = "python313"
$ENTRY_POINT = "process_document_worker"
$SOURCE_DIR = "worker"
$TOPIC_NAME = "document-processing-topic"

Write-Host "Deploying Worker function: $FUNCTION_NAME" -ForegroundColor Green
Write-Host "Project: $PROJECT_ID" -ForegroundColor Cyan
Write-Host "Region: $REGION" -ForegroundColor Cyan
Write-Host "Runtime: $RUNTIME" -ForegroundColor Cyan
Write-Host "Topic: $TOPIC_NAME" -ForegroundColor Cyan

gcloud functions deploy $FUNCTION_NAME `
    --gen2 `
    --runtime=$RUNTIME `
    --region=$REGION `
    --source=$SOURCE_DIR `
    --entry-point=$ENTRY_POINT `
    --trigger-topic=$TOPIC_NAME `
    --project=$PROJECT_ID

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nWorker deployment successful!" -ForegroundColor Green
} else {
    Write-Host "`nDeployment failed!" -ForegroundColor Red
    exit 1
}

