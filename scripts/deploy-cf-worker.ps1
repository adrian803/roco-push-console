#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$CloudflareApiToken = "",
    [string]$RoComApiKey = "",
    [string]$ServerChanSendkey = "",
    [string]$TriggerToken = "",
    [switch]$ConfigureSecrets,
    [switch]$SkipChecks,
    [switch]$SkipTokenVerify,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$WorkerDir = Join-Path $RepoRoot "cf-workers"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

function Read-SecretText {
    param(
        [Parameter(Mandatory = $true)][string]$Prompt,
        [switch]$Optional
    )

    $secure = Read-Host $Prompt -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }

    if (-not $Optional -and [string]::IsNullOrWhiteSpace($plain)) {
        throw "$Prompt cannot be empty."
    }

    return $plain.Trim()
}

function Set-WorkerSecret {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return
    }

    Write-Step "Setting Worker secret $Name"
    $Value | npx wrangler secret put $Name
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to set Worker secret: $Name"
    }
}

function Get-DeployUrl {
    param([string[]]$DeployOutput)

    foreach ($line in $DeployOutput) {
        if ($line -match "https://([a-zA-Z0-9.-]+\.workers\.dev)") {
            return $Matches[1]
        }
    }

    return ""
}

if (-not (Test-Path $WorkerDir)) {
    throw "Cannot find cf-workers directory: $WorkerDir"
}

$HadToken = Test-Path Env:CLOUDFLARE_API_TOKEN
$PreviousToken = if ($HadToken) { $env:CLOUDFLARE_API_TOKEN } else { "" }
$TokenWasSetByScript = $false

try {
    if (-not $DryRun) {
        if (-not [string]::IsNullOrWhiteSpace($CloudflareApiToken)) {
            $env:CLOUDFLARE_API_TOKEN = $CloudflareApiToken.Trim()
            $TokenWasSetByScript = $true
        }
        elseif ([string]::IsNullOrWhiteSpace($env:CLOUDFLARE_API_TOKEN)) {
            $env:CLOUDFLARE_API_TOKEN = Read-SecretText "Cloudflare API token"
            $TokenWasSetByScript = $true
        }

        if (-not $SkipTokenVerify) {
            Write-Step "Verifying Cloudflare API token"
            $verify = Invoke-RestMethod `
                -Uri "https://api.cloudflare.com/client/v4/user/tokens/verify" `
                -Headers @{ Authorization = "Bearer $env:CLOUDFLARE_API_TOKEN" } `
                -Method Get
            if (-not $verify.success) {
                throw "Cloudflare API token verification failed."
            }
        }
    }

    Push-Location $WorkerDir
    try {
        Write-Step "Installing Worker dependencies: npm ci"
        Invoke-External "npm" @("ci")

        if (-not $SkipChecks) {
            Write-Step "Running Worker tests: npm test"
            Invoke-External "npm" @("test")

            Write-Step "Running TypeScript check: npx tsc --noEmit"
            Invoke-External "npx" @("tsc", "--noEmit")

            Write-Step "Checking generated _worker.js: npm run check:worker"
            Invoke-External "npm" @("run", "check:worker")
        }

        if ($DryRun -and (
            $ConfigureSecrets `
            -or -not [string]::IsNullOrWhiteSpace($RoComApiKey) `
            -or -not [string]::IsNullOrWhiteSpace($ServerChanSendkey) `
            -or -not [string]::IsNullOrWhiteSpace($TriggerToken)
        )) {
            Write-Host "Dry run skips Worker secret configuration." -ForegroundColor Yellow
        }

        $ShouldConfigureSecrets = -not $DryRun -and ($ConfigureSecrets `
            -or -not [string]::IsNullOrWhiteSpace($RoComApiKey) `
            -or -not [string]::IsNullOrWhiteSpace($ServerChanSendkey) `
            -or -not [string]::IsNullOrWhiteSpace($TriggerToken))

        if ($ShouldConfigureSecrets) {
            if ([string]::IsNullOrWhiteSpace($RoComApiKey) -and $ConfigureSecrets) {
                $RoComApiKey = Read-SecretText "ROCOM_API_KEY"
            }
            if ([string]::IsNullOrWhiteSpace($ServerChanSendkey) -and $ConfigureSecrets) {
                $ServerChanSendkey = Read-SecretText "SERVERCHAN_SENDKEY (empty to skip)" -Optional
            }
            if ([string]::IsNullOrWhiteSpace($TriggerToken) -and $ConfigureSecrets) {
                $TriggerToken = Read-SecretText "TRIGGER_TOKEN (empty to skip)" -Optional
            }

            Set-WorkerSecret "ROCOM_API_KEY" $RoComApiKey
            Set-WorkerSecret "SERVERCHAN_SENDKEY" $ServerChanSendkey
            Set-WorkerSecret "TRIGGER_TOKEN" $TriggerToken
        }

        if ($DryRun) {
            Write-Step "Running Wrangler dry run: wrangler deploy --dry-run"
            Invoke-External "npx" @("wrangler", "deploy", "--dry-run", "--outdir", "dist")
            Write-Host ""
            Write-Host "Dry run finished. No Worker was deployed." -ForegroundColor Green
            return
        }

        Write-Step "Deploying Cloudflare Worker: wrangler deploy"
        $deployOutput = & npx wrangler deploy 2>&1 | Tee-Object -Variable capturedOutput
        if ($LASTEXITCODE -ne 0) {
            throw "wrangler deploy failed."
        }

        $WorkerHost = Get-DeployUrl $capturedOutput
        if (-not [string]::IsNullOrWhiteSpace($WorkerHost)) {
            Write-Step "Checking Worker health"
            $health = Invoke-RestMethod -Uri "https://$WorkerHost/" -Method Get
            if (-not $health.ok) {
                throw "Worker health check did not return ok=true."
            }
            Write-Host ""
            Write-Host "Deployed successfully: https://$WorkerHost/" -ForegroundColor Green
        }
        else {
            Write-Host ""
            Write-Host "Deployed successfully. Wrangler did not print a workers.dev URL to verify." -ForegroundColor Green
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($HadToken) {
        $env:CLOUDFLARE_API_TOKEN = $PreviousToken
    }
    elseif ($TokenWasSetByScript) {
        Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
    }
}
