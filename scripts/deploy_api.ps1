# Deploy API Cloud Function
# Usage: .\scripts\deploy_api.ps1

$PROJECT_ID = "documentformatterapp"
$REGION = "asia-southeast1"
$FUNCTION_NAME = "api"
$RUNTIME = "python313"
$ENTRY_POINT = "process_document_stable"
$SOURCE_DIR = "api"

Write-Host "Deploying API function: $FUNCTION_NAME" -ForegroundColor Green
Write-Host "Project: $PROJECT_ID" -ForegroundColor Cyan
Write-Host "Region: $REGION" -ForegroundColor Cyan
Write-Host "Runtime: $RUNTIME" -ForegroundColor Cyan

gcloud functions deploy $FUNCTION_NAME `
    --gen2 `
    --runtime=$RUNTIME `
    --region=$REGION `
    --source=$SOURCE_DIR `
    --entry-point=$ENTRY_POINT `
    --trigger-http `
    --allow-unauthenticated `
    --project=$PROJECT_ID

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nAPI deployment successful!" -ForegroundColor Green
    Write-Host "Function URL: https://$REGION-$PROJECT_ID.cloudfunctions.net/$FUNCTION_NAME" -ForegroundColor Yellow
} else {
    Write-Host "`nDeployment failed!" -ForegroundColor Red
    exit 1
}

