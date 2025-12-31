# Deployment Checklist

## ✅ Source Validation

### Signed URL Check
- ✅ No `generate_signed_url` calls found
- ✅ No `Blob.generate_signed_url` calls found
- ✅ No `sign_blob` calls found
- ✅ No `service_account.Credentials` for signing found
- ✅ Only match: Runtime tripwire check (expected)

### Firebase Token URL Implementation
- ✅ Worker uses `upload_from_string()` with bytes
- ✅ Sets `blob.metadata = {"firebaseStorageDownloadTokens": token}` after upload
- ✅ Calls `blob.patch()` to persist metadata
- ✅ Calls `blob.reload()` to verify
- ✅ Constructs Firebase token URL: `https://firebasestorage.googleapis.com/v0/b/{bucket}/o/{encoded}?alt=media&token={token}`
- ✅ Runtime tripwire checks for signed URLs before writing to Firestore
- ✅ Logs `DOWNLOAD_URL=` for debugging

## ✅ Repo Hygiene

### Files Created
- ✅ `.gitignore` - Excludes secrets, credentials, Python cache, IDE files
- ✅ `scripts/deploy_api.ps1` - PowerShell deployment script
- ✅ `scripts/deploy_api.sh` - Bash deployment script
- ✅ `scripts/deploy_worker.ps1` - PowerShell worker deployment
- ✅ `scripts/deploy_worker.sh` - Bash worker deployment
- ✅ `scripts/test_endpoints.ps1` - PowerShell test script
- ✅ `README.md` - Comprehensive documentation

### Requirements Files
- ✅ `api/requirements.txt` - API dependencies (pinned major versions)
- ✅ `worker/requirements.txt` - Worker dependencies (pinned major versions)

## ✅ Documentation

- ✅ Architecture overview
- ✅ API endpoint documentation with examples
- ✅ Firestore schema documentation
- ✅ Storage path format documentation
- ✅ Deployment instructions
- ✅ Testing instructions
- ✅ Troubleshooting section

## Git Commands

If git is not initialized, run these commands in order:

```powershell
# Initialize git repository
git init

# Add all files (respects .gitignore)
git add .

# Commit with message
git commit -m "Backend-first v1: realtime jobs, manual router, firebase token URLs"

# Add remote (replace with your actual GitHub repo URL)
git remote add origin https://github.com/YOUR_USERNAME/DocumentFormatter.git

# Push to main branch
git push -u origin main
```

If git is already initialized:

```powershell
# Check status
git status

# Add all changes
git add .

# Commit with message
git commit -m "Backend-first v1: realtime jobs, manual router, firebase token URLs"

# Push to main
git push origin main
```

## Post-Deployment Verification

1. **Test API endpoint:**
   ```powershell
   .\scripts\test_endpoints.ps1
   ```

2. **Check worker logs:**
   ```powershell
   gcloud functions logs read worker --region=asia-southeast1 --limit=50
   ```

3. **Verify Firestore document:**
   - Check `jobs/{doc_id}` has both `state` and `status` fields
   - Verify `download_url` is a Firebase token URL (not signed URL)
   - Confirm no "private key to sign" errors in logs

4. **Test real-time flow:**
   - Create job via API
   - Subscribe to `jobs/{doc_id}` in Firestore
   - Verify state transitions: QUEUED → PROCESSING → COMPLETED

