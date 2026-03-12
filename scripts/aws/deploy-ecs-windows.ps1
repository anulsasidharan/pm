param(
    [Parameter(Mandatory = $true)]
    [string]$Region,

    [Parameter(Mandatory = $false)]
    [string]$AppName = "pm-app",

    [Parameter(Mandatory = $false)]
    [string]$ImageTag = "v1",

    [Parameter(Mandatory = $true)]
    [string]$ClusterName,

    [Parameter(Mandatory = $true)]
    [string]$ServiceName,

    [Parameter(Mandatory = $false)]
    [string]$TaskFamily = "pm-app-task",

    [Parameter(Mandatory = $true)]
    [string]$ExecutionRoleArn,

    [Parameter(Mandatory = $false)]
    [string]$TaskRoleArn,

    [Parameter(Mandatory = $true)]
    [string]$OpenRouterSecretArn,

    [Parameter(Mandatory = $true)]
    [string]$SessionSecretArn,

    [Parameter(Mandatory = $true)]
    [string]$EfsFileSystemId,

    [Parameter(Mandatory = $true)]
    [string]$TargetGroupArn,

    [Parameter(Mandatory = $true)]
    [string[]]$PrivateSubnetIds,

    [Parameter(Mandatory = $true)]
    [string]$EcsSecurityGroupId,

    [Parameter(Mandatory = $false)]
    [switch]$CreateEcrRepo,

    [Parameter(Mandatory = $false)]
    [switch]$CreateService
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

Write-Step "Validating required CLIs"
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI not found. Install AWS CLI v2 and run aws configure."
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI not found. Install Docker Desktop and ensure it is running."
}

Write-Step "Reading AWS account id"
$AccountId = aws sts get-caller-identity --query Account --output text
if (-not $AccountId) {
    throw "Unable to read AWS account id. Check AWS credentials and region access."
}

$RepoName = $AppName
$ImageUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/$RepoName:$ImageTag"
$LogGroup = "/ecs/$AppName"

if ($CreateEcrRepo) {
    Write-Step "Ensuring ECR repository exists: $RepoName"
    try {
        aws ecr describe-repositories --repository-names $RepoName --region $Region | Out-Null
    }
    catch {
        aws ecr create-repository --repository-name $RepoName --region $Region | Out-Null
    }
}

Write-Step "Logging in to ECR"
$loginToken = aws ecr get-login-password --region $Region
$loginToken | docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com" | Out-Null

Write-Step "Building and pushing Docker image: $ImageUri"
docker build -t "$AppName`:$ImageTag" . | Out-Host
docker tag "$AppName`:$ImageTag" $ImageUri | Out-Host
docker push $ImageUri | Out-Host

Write-Step "Ensuring CloudWatch log group exists: $LogGroup"
$existingLogGroup = aws logs describe-log-groups --log-group-name-prefix $LogGroup --region $Region --query "logGroups[?logGroupName=='$LogGroup'].logGroupName" --output text
if (-not $existingLogGroup) {
    aws logs create-log-group --log-group-name $LogGroup --region $Region | Out-Null
}

Write-Step "Building task definition payload"
$taskDef = @{
    family = $TaskFamily
    networkMode = "awsvpc"
    requiresCompatibilities = @("FARGATE")
    cpu = "512"
    memory = "1024"
    executionRoleArn = $ExecutionRoleArn
    containerDefinitions = @(
        @{
            name = $AppName
            image = $ImageUri
            essential = $true
            portMappings = @(
                @{
                    containerPort = 8000
                    hostPort = 8000
                    protocol = "tcp"
                }
            )
            environment = @(
                @{
                    name = "PYTHONUNBUFFERED"
                    value = "1"
                }
            )
            secrets = @(
                @{
                    name = "OPENROUTER_API_KEY"
                    valueFrom = $OpenRouterSecretArn
                }
                @{
                    name = "PM_SESSION_SECRET"
                    valueFrom = $SessionSecretArn
                }
            )
            mountPoints = @(
                @{
                    sourceVolume = "pm-data"
                    containerPath = "/app/data"
                    readOnly = $false
                }
            )
            logConfiguration = @{
                logDriver = "awslogs"
                options = @{
                    "awslogs-group" = $LogGroup
                    "awslogs-region" = $Region
                    "awslogs-stream-prefix" = "ecs"
                }
            }
        }
    )
    volumes = @(
        @{
            name = "pm-data"
            efsVolumeConfiguration = @{
                fileSystemId = $EfsFileSystemId
                transitEncryption = "ENABLED"
                rootDirectory = "/"
                authorizationConfig = @{
                    iam = "ENABLED"
                }
            }
        }
    )
}

if ($TaskRoleArn) {
    $taskDef.taskRoleArn = $TaskRoleArn
}

$tempTaskPath = Join-Path $env:TEMP "pm-taskdef-$([System.Guid]::NewGuid().ToString()).json"
$taskDef | ConvertTo-Json -Depth 20 | Set-Content -Path $tempTaskPath -Encoding UTF8

Write-Step "Registering task definition"
$registerOut = aws ecs register-task-definition --cli-input-json "file://$tempTaskPath" --region $Region
$taskDefArn = ($registerOut | ConvertFrom-Json).taskDefinition.taskDefinitionArn
if (-not $taskDefArn) {
    throw "Failed to register task definition."
}

Write-Host "Task definition registered: $taskDefArn" -ForegroundColor Green

Write-Step "Checking whether ECS service exists"
$serviceArn = aws ecs describe-services --cluster $ClusterName --services $ServiceName --region $Region --query "services[0].serviceArn" --output text
$serviceExists = $serviceArn -and $serviceArn -ne "None"

if ($serviceExists) {
    Write-Step "Updating service to latest task definition"
    aws ecs update-service --cluster $ClusterName --service $ServiceName --task-definition $taskDefArn --region $Region | Out-Null
}
elseif ($CreateService) {
    Write-Step "Creating ECS service"
    aws ecs create-service --cluster $ClusterName --service-name $ServiceName --task-definition $taskDefArn --desired-count 1 --launch-type FARGATE --platform-version LATEST --network-configuration "awsvpcConfiguration={subnets=[$($PrivateSubnetIds -join ',')],securityGroups=[$EcsSecurityGroupId],assignPublicIp=DISABLED}" --load-balancers "targetGroupArn=$TargetGroupArn,containerName=$AppName,containerPort=8000" --region $Region | Out-Null
}
else {
    throw "Service '$ServiceName' was not found in cluster '$ClusterName'. Re-run with -CreateService to create it."
}

Write-Step "Waiting for ECS service stability"
aws ecs wait services-stable --cluster $ClusterName --services $ServiceName --region $Region

Write-Host "Deployment complete." -ForegroundColor Green
Write-Host "Image URI: $ImageUri"
Write-Host "Service: $ServiceName in cluster $ClusterName"
Write-Host "Health endpoint should be available at your ALB domain on /api/health"
