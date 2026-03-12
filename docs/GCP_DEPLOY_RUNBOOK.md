# GCP Deployment Runbook (Compute Engine + Artifact Registry + Persistent Disk)

## Purpose
Deploy this Project Management MVP to Google Cloud Platform using the current single-container Docker image.

This runbook is tailored to this repo:
- One container serves both frontend and FastAPI backend.
- SQLite is used for persistence and must be stored on persistent disk.
- AI calls require `OPENROUTER_API_KEY`.

## Target Architecture
- Artifact Registry: stores Docker images.
- Compute Engine VM: runs the container with Docker.
- Persistent Disk: stores SQLite data and survives VM recreation.
- Secret Manager: stores application secrets.
- Cloud Logging: container and VM logs.
- Cloud DNS (optional): custom domain DNS.

## Important Constraints
- Keep one app instance for MVP because SQLite is a single-file database and this app is not designed for multi-writer scale.
- Persist `/app/data` to a mounted Persistent Disk so SQLite survives restarts and upgrades.
- For production HTTPS, set cookie security to `secure=True` (or make this env-driven in code).

---

## 1) Prerequisites

### Local tools
- Google Cloud SDK installed (`gcloud`).
- Docker installed and running.
- IAM permissions to create Artifact Registry, Compute Engine VM, disks, firewall rules, Secret Manager secrets, and DNS records.

### Inputs you need
- GCP project ID.
- Region (example: `us-central1`).
- Zone (example: `us-central1-a`).
- OpenRouter API key.
- Strong random session secret for `PM_SESSION_SECRET`.
- Optional custom domain name.

---

## 2) Define Shell Variables (PowerShell)
Run from repo root.

```powershell
$PROJECT_ID = "<your-project-id>"
$REGION = "us-central1"
$ZONE = "us-central1-a"
$APP_NAME = "pm-app"
$REPO = "pm-repo"
$IMAGE_TAG = "v1"
$DISK_NAME = "pm-data-disk"
$VM_NAME = "pm-app-vm"

gcloud config set project $PROJECT_ID
gcloud config set compute/region $REGION
gcloud config set compute/zone $ZONE
```

---

## 3) Enable Required APIs

```powershell
gcloud services enable artifactregistry.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable logging.googleapis.com
```

---

## 4) Create Artifact Registry Repository

```powershell
gcloud artifacts repositories create $REPO --repository-format=docker --location=$REGION --description="PM app images"
```

Configure Docker auth for Artifact Registry:

```powershell
gcloud auth configure-docker "$REGION-docker.pkg.dev"
```

---

## 5) Build and Push Docker Image

```powershell
$IMAGE_URI = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$APP_NAME:$IMAGE_TAG"

docker build -t "$APP_NAME:$IMAGE_TAG" .
docker tag "$APP_NAME:$IMAGE_TAG" $IMAGE_URI
docker push $IMAGE_URI
```

---

## 6) Create Secrets in Secret Manager

```powershell
"REPLACE_WITH_OPENROUTER_API_KEY" | gcloud secrets create openrouter-api-key --data-file=-
"REPLACE_WITH_LONG_RANDOM_SECRET" | gcloud secrets create pm-session-secret --data-file=-
```

If secrets already exist, add a new version instead:

```powershell
"REPLACE_WITH_OPENROUTER_API_KEY" | gcloud secrets versions add openrouter-api-key --data-file=-
"REPLACE_WITH_LONG_RANDOM_SECRET" | gcloud secrets versions add pm-session-secret --data-file=-
```

---

## 7) Create and Attach Persistent Disk

```powershell
gcloud compute disks create $DISK_NAME --size=10GB --type=pd-balanced --zone=$ZONE
```

---

## 8) Create Service Account and Permissions
Create a dedicated service account for the VM:

```powershell
gcloud iam service-accounts create pm-app-sa --display-name="PM App VM Service Account"
```

Grant required roles:

```powershell
$SA_EMAIL = "pm-app-sa@$PROJECT_ID.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/artifactregistry.reader"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/logging.logWriter"
```

---

## 9) Create Startup Script for VM
Create a local file named `scripts/gcp-startup.sh` with this content:

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_NAME="pm-app"
REGION="__REGION__"
PROJECT_ID="__PROJECT_ID__"
REPO="__REPO__"
IMAGE_TAG="__IMAGE_TAG__"
IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$APP_NAME:$IMAGE_TAG"

apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release jq

if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

systemctl enable docker
systemctl start docker

mkdir -p /mnt/pm-data

if ! blkid /dev/disk/by-id/google-pm-data-disk >/dev/null 2>&1; then
  mkfs.ext4 -F /dev/disk/by-id/google-pm-data-disk
fi

if ! grep -q "/mnt/pm-data" /etc/fstab; then
  echo "/dev/disk/by-id/google-pm-data-disk /mnt/pm-data ext4 defaults,nofail 0 2" >> /etc/fstab
fi

mount -a

OPENROUTER_API_KEY=$(gcloud secrets versions access latest --secret=openrouter-api-key)
PM_SESSION_SECRET=$(gcloud secrets versions access latest --secret=pm-session-secret)

cat > /opt/pm.env <<EOF
OPENROUTER_API_KEY=$OPENROUTER_API_KEY
PM_SESSION_SECRET=$PM_SESSION_SECRET
PYTHONUNBUFFERED=1
EOF

gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
docker pull "$IMAGE_URI"

docker rm -f "$APP_NAME" || true
docker run -d \
  --name "$APP_NAME" \
  --restart unless-stopped \
  --env-file /opt/pm.env \
  -p 80:8000 \
  -v /mnt/pm-data:/app/data \
  "$IMAGE_URI"
```

Update placeholders in the script before using it:
- `__REGION__`
- `__PROJECT_ID__`
- `__REPO__`
- `__IMAGE_TAG__`

---

## 10) Create VM and Attach Disk

```powershell
gcloud compute instances create $VM_NAME `
  --zone=$ZONE `
  --machine-type=e2-small `
  --service-account=$SA_EMAIL `
  --scopes=https://www.googleapis.com/auth/cloud-platform `
  --disk=name=$DISK_NAME,device-name=pm-data-disk,mode=rw,boot=no,auto-delete=no `
  --metadata-from-file startup-script=scripts/gcp-startup.sh `
  --tags=pm-app,http-server
```

Create firewall rule to allow HTTP:

```powershell
gcloud compute firewall-rules create pm-app-allow-http --allow tcp:80 --target-tags pm-app --source-ranges 0.0.0.0/0
```

Optional: reserve and assign static external IP.

---

## 11) Validate Deployment
Get VM external IP:

```powershell
$EXTERNAL_IP = gcloud compute instances describe $VM_NAME --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)"
"http://$EXTERNAL_IP"
```

Validation checks:
1. App URL opens.
2. Health endpoint returns OK:

```text
GET http://<vm-external-ip>/api/health
Expected: {"status":"ok"}
```

3. Log in with MVP credentials:
- Username: `user`
- Password: `password`

4. Create/update board cards.
5. Reboot VM and verify data still exists.

---

## 12) Configure HTTPS and Domain (Recommended)
Simplest production path:
1. Reserve static external IP.
2. Point DNS A record to static IP.
3. Install and configure reverse proxy (Nginx or Caddy) on VM.
4. Use Let's Encrypt certificate and enforce HTTPS redirect.
5. Update app cookie settings to `secure=True` for HTTPS.

---

## 13) Deploy New Versions
For each release:
1. Build/push new image tag to Artifact Registry.
2. Update startup script image tag placeholder.
3. Restart container on VM with the new image.
4. Validate health and app behavior.

Example VM update command:

```powershell
$IMAGE_TAG = "v2"
$IMAGE_URI = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$APP_NAME:$IMAGE_TAG"

docker build -t "$APP_NAME:$IMAGE_TAG" .
docker tag "$APP_NAME:$IMAGE_TAG" $IMAGE_URI
docker push $IMAGE_URI

gcloud compute ssh $VM_NAME --zone=$ZONE --command "sudo docker pull $IMAGE_URI && sudo docker rm -f $APP_NAME || true && sudo docker run -d --name $APP_NAME --restart unless-stopped --env-file /opt/pm.env -p 80:8000 -v /mnt/pm-data:/app/data $IMAGE_URI"
```

---

## 14) Observability and Operations
Minimum recommended alerts:
- VM instance down.
- High CPU or memory sustained.
- Health check failing.

Also enable:
- Cloud Monitoring uptime checks on `/api/health`.
- Log-based alert for recurring container startup failures.
- Snapshot schedule for Persistent Disk backups.

---

## 15) Security Hardening Checklist
- Use least-privilege IAM roles for service account.
- Keep secrets in Secret Manager only.
- Restrict inbound firewall rules to required ports.
- Enforce HTTPS for public access.
- Set cookie `secure=True` in production.
- Rotate OpenRouter and session secrets periodically.

---

## 16) Troubleshooting Quick Reference
- VM started but app not available:
  - Check startup script logs: `/var/log/syslog`.
  - Check container status: `sudo docker ps -a`.
  - Check app logs: `sudo docker logs pm-app`.
- Image pull fails:
  - Verify Artifact Registry image exists.
  - Verify VM service account has `roles/artifactregistry.reader`.
- Secrets not loading:
  - Verify service account has `roles/secretmanager.secretAccessor`.
  - Verify secret names are correct.
- Data not persisting:
  - Verify disk is mounted to `/mnt/pm-data`.
  - Verify container bind mount maps `/mnt/pm-data` to `/app/data`.
  - Verify SQLite file exists at `/mnt/pm-data/app.db` on VM.
