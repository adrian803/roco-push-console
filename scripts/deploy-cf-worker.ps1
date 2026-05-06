#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet("", "Source", "WorkerJs")]
    [string]$DeployMode = "",
    [string]$WorkerName = "",
    [string]$CloudflareApiToken = "",
    [string]$RoComApiKey = "",
    [string]$ServerChanSendkey = "",
    [string]$TriggerToken = "",
    [switch]$ConfigureSecrets,
    [switch]$NonInteractive,
    [switch]$SkipChecks,
    [switch]$SkipTokenVerify,
    [switch]$NoPause,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptPath = if ($PSCommandPath) { $PSCommandPath } else { $MyInvocation.MyCommand.Path }
$ScriptDir = Split-Path -Parent $ScriptPath

function Get-ParentProcessName {
    try {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $PID"
        if (-not $process) {
            return ""
        }
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId = $($process.ParentProcessId)"
        if (-not $parent) {
            return ""
        }
        return [System.IO.Path]::GetFileNameWithoutExtension($parent.Name).ToLowerInvariant()
    }
    catch {
        return ""
    }
}

function Start-PersistentConsoleIfNeeded {
    if ($NonInteractive -or $NoPause -or $env:ROCO_DEPLOY_PERSISTENT_WINDOW -eq "1") {
        return
    }

    $parentName = Get-ParentProcessName
    if ($parentName -notin @("explorer", "openwith")) {
        return
    }

    $powerShellExe = Join-Path $PSHOME "powershell.exe"
    if (-not (Test-Path $powerShellExe)) {
        $powerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    }
    if (-not (Test-Path $powerShellExe)) {
        $powerShellExe = "powershell.exe"
    }
    $workDir = Split-Path -Parent $ScriptDir
    $command = "chcp 65001 >nul & `"$powerShellExe`" -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" -NoPause & echo. & echo 执行结束，按任意键关闭窗口... & pause >nul"

    try {
        $env:ROCO_DEPLOY_PERSISTENT_WINDOW = "1"
        Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $command) -WorkingDirectory $workDir
        exit 0
    }
    finally {
        Remove-Item Env:ROCO_DEPLOY_PERSISTENT_WINDOW -ErrorAction SilentlyContinue
    }
}

Start-PersistentConsoleIfNeeded

$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$WorkerDir = Join-Path $RepoRoot "cloudflare-worker"
$WranglerToml = Join-Path $WorkerDir "wrangler.toml"
$WorkerJsPath = Join-Path $WorkerDir "_worker.js"
$WorkerJsTempConfig = Join-Path $WorkerDir ".wrangler-worker-js.tmp.toml"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Wait-BeforeExit {
    if ($NonInteractive -or $NoPause) {
        return
    }

    try {
        [void](Read-Host "执行结束，按回车键退出")
    }
    catch {
        # Some hosts do not support Read-Host during shutdown; cleanup must still finish.
    }
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "命令执行失败：$FilePath $($Arguments -join ' ')"
    }
}

function Read-YesNo {
    param(
        [Parameter(Mandatory = $true)][string]$Prompt,
        [bool]$DefaultYes = $true
    )

    $suffix = if ($DefaultYes) { "[Y/n]" } else { "[y/N]" }
    while ($true) {
        $answer = (Read-Host "$Prompt $suffix").Trim().ToLowerInvariant()
        if ([string]::IsNullOrWhiteSpace($answer)) {
            return $DefaultYes
        }
        if ($answer -in @("y", "yes")) {
            return $true
        }
        if ($answer -in @("n", "no")) {
            return $false
        }
        Write-Host "请输入 y 或 n。" -ForegroundColor Yellow
    }
}

function Read-DeployMode {
    while ($true) {
        Write-Host ""
        Write-Host "请选择部署方式："
        Write-Host "  1. npx 编译/项目部署（src/index.ts + wrangler.toml，推荐）"
        Write-Host "  2. 直接部署项目内 _worker.js（不重新生成 _worker.js）"
        $answer = (Read-Host "请输入 1 或 2，直接回车默认 1").Trim()
        if ([string]::IsNullOrWhiteSpace($answer) -or $answer -eq "1") {
            return "Source"
        }
        if ($answer -eq "2") {
            return "WorkerJs"
        }
        Write-Host "输入无效，请输入 1 或 2。" -ForegroundColor Yellow
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
        throw "$Prompt 不能为空。"
    }

    return $plain.Trim()
}

function Get-ConfiguredWorkerName {
    $content = Get-Content -Path $WranglerToml -Raw
    if ($content -match '(?m)^\s*name\s*=\s*"([^"]+)"') {
        return $Matches[1]
    }
    throw "无法从 $WranglerToml 读取 Worker 名称。"
}

function New-TempWranglerConfig {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Main
    )

    $content = Get-Content -Path $WranglerToml -Raw
    $content = $content -replace '(?m)^\s*name\s*=\s*"[^"]+"\s*$', "name = `"$Name`""
    $content = $content -replace '(?m)^\s*main\s*=\s*"[^"]+"\s*$', "main = `"$Main`""
    Set-Content -Path $WorkerJsTempConfig -Value $content -Encoding UTF8
    return $WorkerJsTempConfig
}

function Set-WorkerSecret {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][string]$TargetWorkerName
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return
    }

    Write-Step "写入 Worker secret：wrangler secret put $Name"
    $Value | npx wrangler secret put $Name --name $TargetWorkerName
    if ($LASTEXITCODE -ne 0) {
        throw "写入 Worker secret 失败：$Name"
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
    throw "找不到 cloudflare-worker 目录：$WorkerDir"
}
if (-not (Test-Path $WranglerToml)) {
    throw "找不到 wrangler.toml：$WranglerToml"
}

$HadToken = Test-Path Env:CLOUDFLARE_API_TOKEN
$PreviousToken = if ($HadToken) { $env:CLOUDFLARE_API_TOKEN } else { "" }
$TokenWasSetByScript = $false
$ActiveConfig = $WranglerToml
$ModeLabel = ""
$ExitCode = 0

try {
    $HasSecretInput = -not [string]::IsNullOrWhiteSpace($RoComApiKey) `
        -or -not [string]::IsNullOrWhiteSpace($ServerChanSendkey) `
        -or -not [string]::IsNullOrWhiteSpace($TriggerToken)

    if ([string]::IsNullOrWhiteSpace($DeployMode)) {
        $DeployMode = if ($NonInteractive) { "Source" } else { Read-DeployMode }
    }

    $ModeLabel = if ($DeployMode -eq "WorkerJs") {
        "直接部署项目内 _worker.js"
    }
    else {
        "npx 编译/项目部署"
    }

    $DefaultWorkerName = Get-ConfiguredWorkerName
    if ([string]::IsNullOrWhiteSpace($WorkerName)) {
        $WorkerName = $DefaultWorkerName
    }

    if (-not $NonInteractive) {
        Write-Host ""
        Write-Host "Cloudflare Worker 交互式部署" -ForegroundColor Green
        Write-Host "部署方式：$ModeLabel"
        Write-Host "Worker 名称：$WorkerName"
        $customName = (Read-Host "如需修改 Worker 名称请输入新名称，直接回车保持不变").Trim()
        if (-not [string]::IsNullOrWhiteSpace($customName)) {
            $WorkerName = $customName
        }

        if ($DeployMode -eq "Source" -and -not $SkipChecks) {
            if (-not (Read-YesNo "部署前运行测试和检查吗？" $true)) {
                $SkipChecks = $true
            }
        }

        if (-not $DryRun -and -not $ConfigureSecrets -and -not $HasSecretInput) {
            if (Read-YesNo "现在配置 Worker secrets 吗？" $true) {
                $ConfigureSecrets = $true
            }
        }
    }

    if (-not $DryRun) {
        if (-not [string]::IsNullOrWhiteSpace($CloudflareApiToken)) {
            $env:CLOUDFLARE_API_TOKEN = $CloudflareApiToken.Trim()
            $TokenWasSetByScript = $true
        }
        elseif ([string]::IsNullOrWhiteSpace($env:CLOUDFLARE_API_TOKEN)) {
            if ($NonInteractive) {
                throw "非交互模式需要先设置 CLOUDFLARE_API_TOKEN，或传入 -CloudflareApiToken。"
            }
            $env:CLOUDFLARE_API_TOKEN = Read-SecretText "Cloudflare API Token"
            $TokenWasSetByScript = $true
        }

        if (-not $SkipTokenVerify) {
            Write-Step "验证 Cloudflare API Token"
            $verify = Invoke-RestMethod `
                -Uri "https://api.cloudflare.com/client/v4/user/tokens/verify" `
                -Headers @{ Authorization = "Bearer $env:CLOUDFLARE_API_TOKEN" } `
                -Method Get
            if (-not $verify.success) {
                throw "Cloudflare API Token 验证失败。"
            }
        }
    }

    Push-Location $WorkerDir
    try {
        Write-Step "安装 Worker 依赖：npm ci"
        Invoke-External "npm" @("ci")

        if ($DeployMode -eq "Source") {
            if ($WorkerName -ne $DefaultWorkerName) {
                $ActiveConfig = New-TempWranglerConfig -Name $WorkerName -Main "src/index.ts"
            }
            if (-not $SkipChecks) {
                Write-Step "运行 Worker 单元测试：npm test"
                Invoke-External "npm" @("test")

                Write-Step "运行 TypeScript 类型检查：npx tsc --noEmit"
                Invoke-External "npx" @("tsc", "--noEmit")

                Write-Step "检查 _worker.js 是否同步：npm run check:worker"
                Invoke-External "npm" @("run", "check:worker")
            }
        }
        else {
            if (-not (Test-Path $WorkerJsPath)) {
                throw "_worker.js 不存在：$WorkerJsPath"
            }
            Write-Step "使用现有 _worker.js，不重新生成"
            $ActiveConfig = New-TempWranglerConfig -Name $WorkerName -Main "_worker.js"
        }

        if ($DryRun -and ($ConfigureSecrets -or $HasSecretInput)) {
            Write-Host "Dry Run 会跳过 Worker secrets 配置。" -ForegroundColor Yellow
        }

        $ShouldConfigureSecrets = -not $DryRun -and ($ConfigureSecrets -or $HasSecretInput)
        if ($ShouldConfigureSecrets) {
            if ([string]::IsNullOrWhiteSpace($RoComApiKey) -and $ConfigureSecrets) {
                if ($NonInteractive) {
                    throw "非交互模式使用 -ConfigureSecrets 时必须传入 -RoComApiKey。"
                }
                $RoComApiKey = Read-SecretText "ROCOM_API_KEY"
            }
            if ([string]::IsNullOrWhiteSpace($ServerChanSendkey) -and $ConfigureSecrets) {
                if (-not $NonInteractive) {
                    $ServerChanSendkey = Read-SecretText "SERVERCHAN_SENDKEY（可留空跳过）" -Optional
                }
            }
            if ([string]::IsNullOrWhiteSpace($TriggerToken) -and $ConfigureSecrets) {
                if (-not $NonInteractive) {
                    $TriggerToken = Read-SecretText "TRIGGER_TOKEN（可留空跳过）" -Optional
                }
            }

            Set-WorkerSecret "ROCOM_API_KEY" $RoComApiKey $WorkerName
            Set-WorkerSecret "SERVERCHAN_SENDKEY" $ServerChanSendkey $WorkerName
            Set-WorkerSecret "TRIGGER_TOKEN" $TriggerToken $WorkerName
        }

        if ($DryRun) {
            Write-Step "执行 Wrangler Dry Run：wrangler deploy --dry-run"
            Invoke-External "npx" @("wrangler", "deploy", "--config", $ActiveConfig, "--dry-run", "--outdir", "dist")
            Write-Host ""
            Write-Host "Dry Run 完成，没有发布 Worker。" -ForegroundColor Green
            return
        }

        Write-Step "发布 Cloudflare Worker：wrangler deploy"
        $deployOutput = & npx wrangler deploy --config $ActiveConfig 2>&1 | Tee-Object -Variable capturedOutput
        if ($LASTEXITCODE -ne 0) {
            throw "wrangler deploy 失败。"
        }

        $WorkerHost = Get-DeployUrl $capturedOutput
        if (-not [string]::IsNullOrWhiteSpace($WorkerHost)) {
            Write-Step "检查 Worker 根路径健康状态"
            $health = Invoke-RestMethod -Uri "https://$WorkerHost/" -Method Get
            if (-not $health.ok) {
                throw "Worker 健康检查没有返回 ok=true。"
            }
            Write-Host ""
            Write-Host "部署成功：https://$WorkerHost/" -ForegroundColor Green
        }
        else {
            Write-Host ""
            Write-Host "部署成功。Wrangler 没有输出 workers.dev 地址，已跳过自动健康检查。" -ForegroundColor Green
        }
    }
    finally {
        Pop-Location
    }
}
catch {
    $ExitCode = 1
    Write-Host ""
    Write-Host "部署失败：$($_.Exception.Message)" -ForegroundColor Red
}
finally {
    if (Test-Path $WorkerJsTempConfig) {
        Remove-Item -LiteralPath $WorkerJsTempConfig -Force -ErrorAction SilentlyContinue
    }
    if ($HadToken) {
        $env:CLOUDFLARE_API_TOKEN = $PreviousToken
    }
    elseif ($TokenWasSetByScript) {
        Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
    }
    Wait-BeforeExit
    if ($ExitCode -ne 0) {
        exit $ExitCode
    }
}
