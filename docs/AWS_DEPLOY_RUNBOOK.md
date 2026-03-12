# AWS Deployment Runbook (ECS Fargate + ECR + ALB + EFS)

## Purpose
Deploy this Project Management MVP to AWS using the current single-container Docker image.

This runbook is tailored to this repo:
- One container serves both frontend and FastAPI backend.
- SQLite is used for persistence and must be stored on persistent shared storage (EFS).
- AI calls require `OPENROUTER_API_KEY`.

## Target Architecture
- Amazon ECR: stores Docker images.
- Amazon ECS (Fargate): runs the container.
- Application Load Balancer (ALB): public HTTP/HTTPS entrypoint.
- AWS Certificate Manager (ACM): TLS certificate.
- Amazon Route 53: DNS record to ALB.
- Amazon EFS: persistent storage for SQLite DB file.
- AWS Secrets Manager: application secrets.
- CloudWatch Logs: container logs.

## Important Constraints
- Keep ECS desired task count at `1` for MVP because SQLite is a single-file database and this app is not designed for multi-writer scale.
- Persist `/app/data` to EFS so SQLite survives task restarts and deployments.
- For production HTTPS, set cookie security to `secure=True` (or make this env-driven in code).

---

## 1) Prerequisites

### Local tools
- AWS CLI v2 installed and configured (`aws configure`).
- Docker installed and running.
- IAM identity with permission to create ECR, ECS, ALB, ACM, Route53, EFS, IAM role policies, and Secrets Manager resources.

### Inputs you need
- AWS region (example: `us-east-1`).
- Domain name hosted in Route 53 (recommended for HTTPS).
- OpenRouter API key.
- Strong random session secret for `PM_SESSION_SECRET`.

---

## 2) Define Shell Variables (PowerShell)
Run from repo root.

```powershell
$AWS_REGION = "us-east-1"
$APP_NAME = "pm-app"
$IMAGE_TAG = "v1"
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$ECR_REPO = $APP_NAME
$IMAGE_URI = "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG"
```

---

## 3) Create ECR Repository

```powershell
aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION
```

Login Docker to ECR:

```powershell
aws ecr get-login-password --region $AWS_REGION |
  docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

---

## 4) Build and Push Docker Image

```powershell
docker build -t "$APP_NAME:$IMAGE_TAG" .
docker tag "$APP_NAME:$IMAGE_TAG" $IMAGE_URI
docker push $IMAGE_URI
```

---

## 5) Create Secrets in Secrets Manager

```powershell
aws secretsmanager create-secret \
  --name "pm/openrouter_api_key" \
  --secret-string "REPLACE_WITH_OPENROUTER_API_KEY" \
  --region $AWS_REGION

aws secretsmanager create-secret \
  --name "pm/session_secret" \
  --secret-string "REPLACE_WITH_LONG_RANDOM_SECRET" \
  --region $AWS_REGION
```

If secrets already exist, use `put-secret-value` instead of `create-secret`.

---

## 6) Networking Setup (VPC/Subnets/Security Groups)
Create or choose:
- 2 public subnets for ALB.
- 2 private subnets for ECS tasks.

Security groups:
- ALB SG:
  - Inbound `80` from `0.0.0.0/0`.
  - Inbound `443` from `0.0.0.0/0`.
  - Outbound all.
- ECS SG:
  - Inbound `8000` from ALB SG only.
  - Outbound all.
- EFS SG:
  - Inbound `2049` (NFS) from ECS SG only.

---

## 7) Create EFS for SQLite Persistence
1. Create EFS file system in the same VPC.
2. Create mount targets in private subnets used by ECS tasks.
3. Attach EFS SG.
4. In task definition, mount EFS volume to container path `/app/data`.

Result: SQLite file `/app/data/app.db` persists across task replacements.

---

## 8) Create ECS Cluster (Fargate)
Create cluster:
- Name: `pm-cluster`
- Infrastructure: Fargate

---

## 9) IAM Roles for ECS
Create or use:
- Task execution role with `AmazonECSTaskExecutionRolePolicy`.

Add permissions for secret retrieval:
- `secretsmanager:GetSecretValue`
- `kms:Decrypt` (if using customer-managed KMS key)

Scope permissions to only required secret ARNs.

---

## 10) Create Task Definition
Create Fargate task definition with:
- Family: `pm-app-task`
- CPU/Memory: start with `0.5 vCPU` and `1 GB`
- Container image: `$IMAGE_URI`
- Port mapping: container `8000`
- Log driver: awslogs (log group `/ecs/pm-app`)
- Secrets:
  - `OPENROUTER_API_KEY` from `pm/openrouter_api_key`
  - `PM_SESSION_SECRET` from `pm/session_secret`
- EFS volume mounted to `/app/data` (read/write)

Recommended runtime env vars:
- `PYTHONUNBUFFERED=1`

---

## 11) Create ALB and Target Group
1. Create ALB in public subnets and attach ALB SG.
2. Create target group:
   - Target type: `ip`
   - Protocol: HTTP
   - Port: `8000`
   - Health check path: `/api/health`
3. Listener rules:
   - Port 80: redirect to HTTPS 443
   - Port 443: forward to target group

---

## 12) Create ACM Certificate and DNS
1. Request ACM certificate in same region as ALB.
2. Validate via Route 53 DNS.
3. Create Route 53 alias `A` record (for example `app.example.com`) to ALB DNS.
4. Attach ACM cert to ALB 443 listener.

---

## 13) Create ECS Service
Create ECS service in `pm-cluster`:
- Launch type: Fargate
- Task definition: latest `pm-app-task`
- Desired count: `1`
- Subnets: private subnets
- Security group: ECS SG
- Public IP: disabled
- Load balancer: attach ALB target group to container port `8000`

Wait for service to stabilize and target group health to become healthy.

---

## 14) Validate Deployment
1. App URL opens over HTTPS.
2. Health endpoint returns OK:

```text
GET https://<your-domain>/api/health
Expected: {"status":"ok"}
```

3. Log in with MVP credentials:
- Username: `user`
- Password: `password`

4. Create/update board cards.
5. Force new ECS deployment and verify data still exists.

---

## 15) Deploy New Versions
For each release:
1. Build/push new image tag to ECR.
2. Register a new task definition revision with the new image tag.
3. Update ECS service to the new revision.
4. Monitor rollout in ECS events and CloudWatch logs.

---

## 16) Observability and Operations
Minimum recommended alarms:
- ALB 5xx count > 0
- Unhealthy target count > 0
- ECS service running task count < desired count

Also enable:
- EFS backup policy
- CloudWatch log retention policy

---

## 17) Security Hardening Checklist
- Use least-privilege IAM policies for roles.
- Restrict ECS SG inbound to ALB SG only.
- Do not store secrets in plaintext env files in AWS.
- Ensure TLS-only public access.
- Set cookie `secure=True` for production HTTPS.
- Rotate OpenRouter and session secrets periodically.

---

## 18) Troubleshooting Quick Reference
- Task stops immediately:
  - Check CloudWatch logs for startup exception.
  - Verify secrets are readable by ECS role.
- ALB target unhealthy:
  - Confirm container is listening on `0.0.0.0:8000`.
  - Confirm health check path is `/api/health`.
  - Verify ECS SG allows inbound 8000 from ALB SG.
- Data not persisting:
  - Confirm EFS volume mounted at `/app/data`.
  - Confirm EFS SG allows NFS 2049 from ECS SG.
- Login/session problems behind HTTPS:
  - Confirm cookie `secure=True` in production.

---

## 19) Optional Next Improvement (Post-MVP)
To scale beyond one task, migrate from SQLite on EFS to Amazon RDS (PostgreSQL), then increase ECS desired count and add autoscaling.

---

## 20) Included Automation Assets in This Repo

- PowerShell deploy script: `scripts/aws/deploy-ecs-windows.ps1`
- ECS task definition template: `scripts/aws/taskdef.template.json`
- ECS service template: `scripts/aws/service.template.json`

### Quick usage for the PowerShell deploy script
Run from repo root after infrastructure (VPC, ALB, target group, EFS, roles, secrets) exists:

```powershell
.\scripts\aws\deploy-ecs-windows.ps1 -Region us-east-1 -ClusterName pm-cluster -ServiceName pm-app-svc -ExecutionRoleArn arn:aws:iam::<account-id>:role/ecsTaskExecutionRole -TaskRoleArn arn:aws:iam::<account-id>:role/pmAppTaskRole -OpenRouterSecretArn arn:aws:secretsmanager:us-east-1:<account-id>:secret:pm/openrouter_api_key-xxxx -SessionSecretArn arn:aws:secretsmanager:us-east-1:<account-id>:secret:pm/session_secret-xxxx -EfsFileSystemId fs-xxxxxxxx -TargetGroupArn arn:aws:elasticloadbalancing:us-east-1:<account-id>:targetgroup/pm-app-tg/xxxxxxxx -PrivateSubnetIds subnet-aaaa,subnet-bbbb -EcsSecurityGroupId sg-ecsxxxxxxxx -CreateEcrRepo
```

For first-time ECS service creation, add `-CreateService`.
