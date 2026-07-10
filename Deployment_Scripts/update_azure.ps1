$ErrorActionPreference = 'Stop'

Write-Host '==========================================' -ForegroundColor Cyan
Write-Host '  Quick Azure Update - KnowledgeAI' -ForegroundColor Cyan
Write-Host '==========================================' -ForegroundColor Cyan

$azAccount = az account show --query name -o tsv 2>$null
if (-not $azAccount) {
    Write-Host 'ERROR: You are not logged into Azure CLI!' -ForegroundColor Red
    Write-Host 'Please run "az login" and try again.' -ForegroundColor Yellow
    exit 1
}
Write-Host ('Logged into Azure Subscription: ' + $azAccount) -ForegroundColor Green

Write-Host ''
Write-Host '[1/3] Finding existing KnowledgeAI deployment...' -ForegroundColor Cyan

# Find the app automatically
$appName = az webapp list --query "[?contains(name, 'knowledgeai-app-')].name | [0]" -o tsv
if (-not $appName) {
    Write-Host 'ERROR: Could not find an existing KnowledgeAI web app.' -ForegroundColor Red
    exit 1
}

$rgName = az webapp list --query "[?name=='$appName'].resourceGroup | [0]" -o tsv
$acrName = az acr list --resource-group $rgName --query "[0].name" -o tsv

Write-Host "Found App: $appName" -ForegroundColor Green
Write-Host "Found Resource Group: $rgName" -ForegroundColor Green
Write-Host "Found Registry: $acrName" -ForegroundColor Green

Write-Host ''
Write-Host '[2/3] Building and Pushing new Docker Image...' -ForegroundColor Cyan
az acr login --name $acrName
docker build -t knowledgeai:latest .
$imageTag = $acrName + '.azurecr.io/knowledgeai:latest'
docker tag knowledgeai:latest $imageTag
docker push $imageTag

Write-Host ''
Write-Host '[3/3] Restarting Web App to pull new image...' -ForegroundColor Cyan
az webapp restart --name $appName --resource-group $rgName | Out-Null

Write-Host ''
Write-Host '==========================================' -ForegroundColor Green
Write-Host 'UPDATE COMPLETE!' -ForegroundColor Green
Write-Host '==========================================' -ForegroundColor Green
Write-Host ('Your updated application is live at: https://' + $appName + '.azurewebsites.net') -ForegroundColor Cyan
