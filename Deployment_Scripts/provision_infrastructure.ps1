param (
    [string]$Subscription = ''
)
$ErrorActionPreference = 'Stop'

Write-Host 'Azure Deployment - KnowledgeAI' -ForegroundColor Cyan
Write-Host '==============================' -ForegroundColor Cyan

$azAccount = az account show --query name -o tsv 2>$null
if (-not $azAccount) {
    Write-Host 'ERROR: You are not logged into Azure CLI!' -ForegroundColor Red
    Write-Host 'Please run "az login" and try again.' -ForegroundColor Yellow
    exit 1
}
Write-Host ('Logged into Azure Subscription: ' + $azAccount) -ForegroundColor Green

if ($Subscription) {
    az account set --subscription $Subscription
}

Write-Host "Please provide the required configuration for the deployment:" -ForegroundColor Yellow
$OpenAIKey = Read-Host "Enter your OpenAI API Key"
$ImageOpenApiKey = Read-Host "Enter your Image OpenAI API Key (press Enter to use the same as OpenAI Key)"
if ([string]::IsNullOrWhiteSpace($ImageOpenApiKey)) {
    $ImageOpenApiKey = $OpenAIKey
}
$ImageProcessingModel = Read-Host "Enter the Image Processing Model (press Enter for 'gpt-4o-mini')"
if ([string]::IsNullOrWhiteSpace($ImageProcessingModel)) {
    $ImageProcessingModel = "gpt-5-mini"
}

Write-Host "Please provide SMTP configuration for emails:" -ForegroundColor Yellow
$SmtpHost = Read-Host "Enter SMTP Host (press Enter for 'smtp-relay.brevo.com')"
if ([string]::IsNullOrWhiteSpace($SmtpHost)) { $SmtpHost = "smtp-relay.brevo.com" }
$SmtpPort = Read-Host "Enter SMTP Port (press Enter for '587')"
if ([string]::IsNullOrWhiteSpace($SmtpPort)) { $SmtpPort = "587" }
$SmtpUser = Read-Host "Enter SMTP Username"
$SmtpPassword = Read-Host "Enter SMTP Password"
$SmtpFromEmail = Read-Host "Enter SMTP From Email (press Enter for 'akshitamishra421@gmail.com')"
if ([string]::IsNullOrWhiteSpace($SmtpFromEmail)) { $SmtpFromEmail = "akshitamishra421@gmail.com" }

$suffix = Get-Random -Minimum 1000 -Maximum 9999
$rgName = 'knowledgeai-rg-' + $suffix
$acrName = 'knowledgeairegistry' + $suffix
$dbName = 'knowledgeai-db-' + $suffix
$appName = 'knowledgeai-app-' + $suffix
$appPlan = 'knowledgeai-plan-' + $suffix

function Generate-RandomString($length) {
    $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    $bytes = New-Object Byte[] $length
    [Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes)
    $result = ''
    foreach ($b in $bytes) { $result += $chars[$b % $chars.Length] }
    return $result
}

$dbPassword = (Generate-RandomString 16) + '1!'
$secretKey = Generate-RandomString 64

$fernetBytes = New-Object Byte[] 32
[Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($fernetBytes)
$fernetKey = [Convert]::ToBase64String($fernetBytes)

$dbUrl = 'postgresql+psycopg://dbadmin:' + $dbPassword + '@' + $dbName + '.postgres.database.azure.com:5432/ragdb'

Write-Host ''
Write-Host '[1/6] Registering required Azure Providers & Creating Resource Group (' + $rgName + ')...' -ForegroundColor Cyan
az provider register --namespace Microsoft.ContainerRegistry | Out-Null
az provider register --namespace Microsoft.DBforPostgreSQL | Out-Null
az provider register --namespace Microsoft.Web | Out-Null
az group create --name $rgName --location southeastasia | Out-Null

Write-Host ''
Write-Host ('[2/6] Creating Container Registry (' + $acrName + ')...') -ForegroundColor Cyan
az acr create --resource-group $rgName --name $acrName --sku Basic --admin-enabled true | Out-Null
$acrPassword = az acr credential show --name $acrName --query 'passwords[0].value' -o tsv

Write-Host ''
Write-Host '[3/6] Building and Pushing Docker Image...' -ForegroundColor Cyan
az acr login --name $acrName
docker build -t knowledgeai:latest .
$imageTag = $acrName + '.azurecr.io/knowledgeai:latest'
docker tag knowledgeai:latest $imageTag
docker push $imageTag

Write-Host ''
Write-Host '[4/6] Creating PostgreSQL Database (this takes a few minutes)...' -ForegroundColor Cyan
az postgres flexible-server create --resource-group $rgName --name $dbName --location southeastasia --admin-user dbadmin --admin-password $dbPassword --sku-name Standard_B1ms --tier Burstable --version 16 --public-access 0.0.0.0 | Out-Null

az postgres flexible-server parameter set --resource-group $rgName --server-name $dbName --name azure.extensions --value vector | Out-Null

az postgres flexible-server db create --resource-group $rgName --server-name $dbName --name ragdb | Out-Null

Write-Host ''
Write-Host ('[5/6] Creating App Service (' + $appName + ')...') -ForegroundColor Cyan
az appservice plan create --resource-group $rgName --name $appPlan --is-linux --sku B1 | Out-Null

az webapp create --resource-group $rgName --plan $appPlan --name $appName --deployment-container-image-name $imageTag | Out-Null

$registryUrl = 'https://' + $acrName + '.azurecr.io'
az webapp config container set --resource-group $rgName --name $appName --docker-registry-server-url $registryUrl --docker-registry-server-user $acrName --docker-registry-server-password $acrPassword | Out-Null

Write-Host ''
Write-Host '[6/6] Configuring Environment Variables...' -ForegroundColor Cyan
$settingsArray = @(
    "DATABASE_URL=$dbUrl",
    "SECRET_KEY=$secretKey",
    "ENCRYPTION_KEY=$fernetKey",
    "OPENAI_API_KEY=$OpenAIKey",
    "IMAGE_OPEN_API_KEY=$ImageOpenApiKey",
    "IMAGE_PROCESSING_MODEL=$ImageProcessingModel",
    "JWT_ALGORITHM=HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES=60",
    "REFRESH_TOKEN_EXPIRE_DAYS=7",
    "APP_ENV=production",
    "WEBSITES_PORT=8000",
    "SMTP_HOST=$SmtpHost",
    "SMTP_PORT=$SmtpPort",
    "SMTP_USER=$SmtpUser",
    "SMTP_PASSWORD=$SmtpPassword",
    "SMTP_FROM_EMAIL=$SmtpFromEmail",
    "SMTP_USE_TLS=true"
)
az webapp config appsettings set --resource-group $rgName --name $appName --settings $settingsArray | Out-Null

Write-Host ''
Write-Host '==========================================' -ForegroundColor Green
Write-Host 'DEPLOYMENT COMPLETE!' -ForegroundColor Green
Write-Host '==========================================' -ForegroundColor Green
Write-Host 'Your application is now live at:'
Write-Host ('https://' + $appName + '.azurewebsites.net') -ForegroundColor Cyan
Write-Host ''
Write-Host 'Note: It may take 3-5 minutes for the container to start up and the database tables to initialize on the very first load.'
