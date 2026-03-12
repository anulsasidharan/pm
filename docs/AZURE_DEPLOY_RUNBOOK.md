# Azure Deployment Runbook (Container Apps + ACR + Azure Files)

## Purpose
Deploy this Project Management MVP to Azure using the current single-container Docker image.

This runbook is tailored to this repo:
- One container serves both frontend and FastAPI backend.
- SQLite is used for persistence and must be stored on persistent shared storage (Azure Files).
- AI calls require `OPENROUTER_API_KEY`.

## Target Architecture
- Azure Container Registry (ACR): stores Docker images.
- Azure Container Apps: runs the container.
- Azure Files (Storage Account + File Share): persistent storage for SQLite DB.
- Azure Key Vault: stores application secrets.
- Azure DNS (optional): custom domain DNS records.
- Log Analytics workspace: container logs and diagnostics.

## Important Constraints
- Keep replica count at `1` for MVP because SQLite is a single-file database and this app is not designed for multi-writer scale.
- Persist `/app/data` to Azure Files so SQLite survives revisions and restarts.
- For production HTTPS, set cookie security to `secure=True` (or make this env-driven in code).

---

## 1) Prerequisites

### Local tools
- Azure CLI installed and logged in (`az login`).
- Docker installed and running.
- Permissions to create resource groups, ACR, Container Apps, Key Vault, Storage, and role assignments.

### Inputs you need
- Azure subscription ID.
- Azure region (example: `eastus`).
- OpenRouter API key.
- Strong random session secret for `PM_SESSION_SECRET`.
- Optional custom domain name for HTTPS.

---

## 2) Define Shell Variables (PowerShell)
Run from repo root.

```powershell
$SUBSCRIPTION_ID = "<your-subscription-id>"
$LOCATION = "eastus"
$RG = "rg-pm-app"
$APP_NAME = "pm-app"
$ACR_NAME = "pma$((Get-Random -Maximum 99999).ToString('00000'))"
$ENV_NAME = "pm-env"
$IMAGE_TAG = "v1"
$STORAGE_ACCOUNT = "pmdat$((Get-Random -Maximum 99999).ToString('00000'))"
$FILE_SHARE = "pm-data"
$KEYVAULT_NAME = "pm-kv-$((Get-Random -Maximum 99999).ToString('00000'))"

az account set --subscription $SUBSCRIPTION_ID
```

Note: names like ACR, storage account, and key vault must be globally unique.

---

## 3) Create Resource Group and Log Analytics

```powershell
az group create --name $RG --location $LOCATION

az monitor log-analytics workspace create \
  --resource-group $RG \
  --workspace-name "$APP_NAME-logs" \
  --location $LOCATION
```

---

## 4) Create Azure Container Registry (ACR)

```powershell
az acr create \
  --resource-group $RG \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled false
```

Login Docker to ACR:

```powershell
az acr login --name $ACR_NAME
```

---

## 5) Build and Push Docker Image

```powershell
$ACR_LOGIN_SERVER = az acr show --name $ACR_NAME --resource-group $RG --query loginServer -o tsv
$IMAGE_URI = "$ACR_LOGIN_SERVER/$APP_NAME:$IMAGE_TAG"

docker build -t "$APP_NAME:$IMAGE_TAG" .
docker tag "$APP_NAME:$IMAGE_TAG" $IMAGE_URI
docker push $IMAGE_URI
```

---

## 6) Create Key Vault and Store Secrets

```powershell
az keyvault create \
  --name $KEYVAULT_NAME \
  --resource-group $RG \
  --location $LOCATION

az keyvault secret set --vault-name $KEYVAULT_NAME --name "openrouter-api-key" --value "REPLACE_WITH_OPENROUTER_API_KEY"
az keyvault secret set --vault-name $KEYVAULT_NAME --name "pm-session-secret" --value "REPLACE_WITH_LONG_RANDOM_SECRET"
```

---

## 7) Create Storage Account and Azure File Share

```powershell
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RG \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2

az storage share-rm create \
  --resource-group $RG \
  --storage-account $STORAGE_ACCOUNT \
  --name $FILE_SHARE \
  --quota 5
```

Get storage key for the Container Apps environment storage binding:

```powershell
$STORAGE_KEY = az storage account keys list \
  --resource-group $RG \
  --account-name $STORAGE_ACCOUNT \
  --query "[0].value" -o tsv
```

---

## 8) Create Container Apps Environment

```powershell
az extension add --name containerapp --upgrade

az containerapp env create \
  --name $ENV_NAME \
  --resource-group $RG \
  --location $LOCATION
```

Attach Azure Files to the environment:

```powershell
az containerapp env storage set \
  --name $ENV_NAME \
  --resource-group $RG \
  --storage-name pmfilestorage \
  --azure-file-account-name $STORAGE_ACCOUNT \
  --azure-file-account-key $STORAGE_KEY \
  --azure-file-share-name $FILE_SHARE \
  --access-mode ReadWrite
```

---

## 9) Create Managed Identity and Grant Permissions
Create a user-assigned managed identity for secret access:

```powershell
az identity create --resource-group $RG --name "$APP_NAME-identity"

$IDENTITY_ID = az identity show --resource-group $RG --name "$APP_NAME-identity" --query id -o tsv
$IDENTITY_PRINCIPAL_ID = az identity show --resource-group $RG --name "$APP_NAME-identity" --query principalId -o tsv
$KEYVAULT_ID = az keyvault show --name $KEYVAULT_NAME --resource-group $RG --query id -o tsv
```

Grant Key Vault secret read permission:

```powershell
az role assignment create \
  --assignee-object-id $IDENTITY_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope $KEYVAULT_ID
```

---

## 10) Deploy Container App

```powershell
az containerapp create \
  --name $APP_NAME \
  --resource-group $RG \
  --environment $ENV_NAME \
  --image $IMAGE_URI \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --user-assigned $IDENTITY_ID \
  --registry-server $ACR_LOGIN_SERVER
```

Configure secrets and env vars (including Key Vault references):

```powershell
$OPENROUTER_SECRET_URI = az keyvault secret show --vault-name $KEYVAULT_NAME --name "openrouter-api-key" --query id -o tsv
$SESSION_SECRET_URI = az keyvault secret show --vault-name $KEYVAULT_NAME --name "pm-session-secret" --query id -o tsv

az containerapp secret set \
  --name $APP_NAME \
  --resource-group $RG \
  --secrets \
  "openrouter-api-key=keyvaultref:$OPENROUTER_SECRET_URI,identityref:$IDENTITY_ID" \
  "pm-session-secret=keyvaultref:$SESSION_SECRET_URI,identityref:$IDENTITY_ID"

az containerapp update \
  --name $APP_NAME \
  --resource-group $RG \
  --set-env-vars \
  OPENROUTER_API_KEY=secretref:openrouter-api-key \
  PM_SESSION_SECRET=secretref:pm-session-secret \
  PYTHONUNBUFFERED=1
```

Mount Azure Files to `/app/data`:

```powershell
$yamlPath = "containerapp-volume.yaml"

@"
properties:
  template:
    containers:
      - name: pm-app
        volumeMounts:
          - volumeName: data-volume
            mountPath: /app/data
    volumes:
      - name: data-volume
        storageType: AzureFile
        storageName: pmfilestorage
"@ | Set-Content -Path $yamlPath

az containerapp update \
  --name $APP_NAME \
  --resource-group $RG \
  --yaml $yamlPath
```

---

## 11) Validate Deployment
Get app URL:

```powershell
$APP_URL = az containerapp show --name $APP_NAME --resource-group $RG --query properties.configuration.ingress.fqdn -o tsv
"https://$APP_URL"
```

Validation checks:
1. App URL opens over HTTPS.
2. Health endpoint returns OK:

```text
GET https://<container-app-fqdn>/api/health
Expected: {"status":"ok"}
```

3. Log in with MVP credentials:
- Username: `user`
- Password: `password`

4. Create/update board cards.
5. Trigger a new revision and verify data still exists.

---

## 12) Configure Custom Domain (Optional)
1. Add custom domain to Container App.
2. Validate DNS ownership record (TXT/CNAME) as prompted.
3. Bind managed certificate.
4. Route public DNS (Azure DNS or external DNS) to the Container App ingress endpoint.

---

## 13) Deploy New Versions
For each release:
1. Build/push new image tag to ACR.
2. Update Container App image to the new tag.
3. Verify healthy new revision and traffic routing.
4. Monitor logs and rollback to prior revision if needed.

Example:

```powershell
$IMAGE_TAG = "v2"
$IMAGE_URI = "$ACR_LOGIN_SERVER/$APP_NAME:$IMAGE_TAG"

docker build -t "$APP_NAME:$IMAGE_TAG" .
docker tag "$APP_NAME:$IMAGE_TAG" $IMAGE_URI
docker push $IMAGE_URI

az containerapp update \
  --name $APP_NAME \
  --resource-group $RG \
  --image $IMAGE_URI
```

---

## 14) Observability and Operations
Minimum recommended alerts:
- Request failure rate above threshold.
- No healthy replica running.
- Restart count unexpectedly high.

Also enable:
- Log Analytics retention policy.
- Storage account backup/replication posture review.

---

## 15) Security Hardening Checklist
- Use least-privilege role assignments.
- Keep secrets in Key Vault only (not in source control).
- Restrict who can pull/push images in ACR.
- Ensure TLS-only public access.
- Set cookie `secure=True` for production HTTPS.
- Rotate OpenRouter and session secrets periodically.

---

## 16) Troubleshooting Quick Reference
- Container fails to start:
  - Check Container Apps revision logs.
  - Verify image exists in ACR and app can pull it.
- Health endpoint failing:
  - Confirm app listens on `0.0.0.0:8000`.
  - Confirm ingress `target-port` is `8000`.
  - Confirm health path `/api/health` works in container logs.
- Secrets not available:
  - Verify managed identity assignment.
  - Verify Key Vault role `Key Vault Secrets User` at correct scope.
  - Verify secret reference names match env var references.
- Data not persisting:
  - Confirm Azure Files volume is mounted at `/app/data`.
  - Confirm SQLite DB path resolves to `/app/data/app.db` in container.
