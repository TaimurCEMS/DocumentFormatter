# Test API Endpoints
# Usage: .\scripts\test_endpoints.ps1

$PROJECT_ID = "documentformatterapp"
$REGION = "asia-southeast1"
$FUNCTION_NAME = "api"
$BASE_URL = "https://$REGION-$PROJECT_ID.cloudfunctions.net/$FUNCTION_NAME"

Write-Host "Testing Document Formatter API" -ForegroundColor Green
Write-Host "Base URL: $BASE_URL`n" -ForegroundColor Cyan

# Test 1: POST /api/process_document_stable
Write-Host "Test 1: POST /api/process_document_stable" -ForegroundColor Yellow
$testStoragePath = "test/input.docx"
$body = @{
    storage_path = $testStoragePath
    style_prompt = "Formal Academic Style"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/process_document_stable" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
    
    Write-Host "Response: " -NoNewline
    $response | ConvertTo-Json | Write-Host
    
    $docId = $response.doc_id
    if (-not $docId) {
        Write-Host "ERROR: No doc_id in response!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "`nCreated job with doc_id: $docId" -ForegroundColor Green
    Write-Host "Waiting 5 seconds for processing..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
    
} catch {
    Write-Host "ERROR: POST request failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Test 2: GET /api/v1/document_result
Write-Host "`nTest 2: GET /api/v1/document_result?doc_id=$docId" -ForegroundColor Yellow
try {
    $result = Invoke-RestMethod -Uri "$BASE_URL/api/v1/document_result?doc_id=$docId" -Method GET
    
    Write-Host "Response: " -NoNewline
    $result | ConvertTo-Json -Depth 5 | Write-Host
    
    Write-Host "`nState: $($result.state)" -ForegroundColor Cyan
    Write-Host "Status: $($result.status)" -ForegroundColor Cyan
    Write-Host "Progress: $($result.progress)%" -ForegroundColor Cyan
    
    if ($result.state -eq "COMPLETED") {
        Write-Host "`nJob completed! Download URL: $($result.download_url)" -ForegroundColor Green
        
        # Test 3: GET /api/v1/document_download
        Write-Host "`nTest 3: GET /api/v1/document_download?doc_id=$docId" -ForegroundColor Yellow
        try {
            $download = Invoke-RestMethod -Uri "$BASE_URL/api/v1/document_download?doc_id=$docId" -Method GET
            Write-Host "Download URL: $($download.url)" -ForegroundColor Green
        } catch {
            Write-Host "Download endpoint returned: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "`nJob still processing. Poll again later." -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "ERROR: GET request failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host "`nAll tests completed!" -ForegroundColor Green

