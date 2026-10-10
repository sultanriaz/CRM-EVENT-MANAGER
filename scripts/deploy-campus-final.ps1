param(
    [string]$Org = 'fitness-trial',
    [switch]$Deploy
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Manifest = Join-Path $ProjectRoot 'manifest\campus-final-package.xml'
$Stage1 = Join-Path $ProjectRoot 'manifest\campus-stage1-foundation.xml'
$Stage2 = Join-Path $ProjectRoot 'manifest\campus-stage2-application.xml'
$Prestage = Join-Path $ProjectRoot 'manifest\campus-prestage-validation.xml'
$Evidence = Join-Path $ProjectRoot 'campus_patch_runs\final_deployment'
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null

function Invoke-SfChecked {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & sf @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Salesforce CLI failed: sf $($Arguments -join ' ')" }
}

Write-Host 'Verifying target org identity...'
Invoke-SfChecked org display --target-org $Org --json

Write-Host 'Creating a metadata backup retrieve (no org mutation)...'
Invoke-SfChecked project retrieve start --manifest $Manifest --target-org $Org --target-metadata-dir (Join-Path $Evidence 'org-backup') --zip-file-name campus-before-deploy.zip --unzip --wait 30

Write-Host 'Validating foundation components...'
Invoke-SfChecked project deploy start --manifest $Stage1 --target-org $Org --dry-run --test-level RunSpecifiedTests --tests EnterpriseWorkspaceControllerTest --wait 60

Write-Host 'Validating all components that do not require foundation state to be committed...'
Invoke-SfChecked project deploy start --manifest $Prestage --target-org $Org --dry-run --test-level RunSpecifiedTests --tests CampusEventRegisterActionTest --tests CampusEventsDashboardControllerTest --tests CampusAutomationActionsTest --tests EnterpriseWorkspaceControllerTest --wait 60

if (-not $Deploy) {
    Write-Host 'Validation complete. Live deployment was NOT requested; stopping safely.'
    exit 0
}

Write-Host 'Deploying Stage 1 foundation after explicit -Deploy opt-in...'
Invoke-SfChecked project deploy start --manifest $Stage1 --target-org $Org --test-level RunSpecifiedTests --tests EnterpriseWorkspaceControllerTest --wait 60

Write-Host 'Validating Stage 2 against the committed foundation...'
Invoke-SfChecked project deploy start --manifest $Stage2 --target-org $Org --dry-run --test-level RunSpecifiedTests --tests CampusEventRegisterActionTest --tests CampusEventsDashboardControllerTest --tests CampusAutomationActionsTest --tests EnterpriseWorkspaceControllerTest --wait 60

Write-Host 'Deploying Stage 2 application...'
Invoke-SfChecked project deploy start --manifest $Stage2 --target-org $Org --test-level RunSpecifiedTests --tests CampusEventRegisterActionTest --tests CampusEventsDashboardControllerTest --tests CampusAutomationActionsTest --tests EnterpriseWorkspaceControllerTest --wait 60
Write-Host 'Deployment finished. Complete the documented post-deployment checks before activating flows.'
