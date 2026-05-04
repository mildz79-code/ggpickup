#requires -Version 5.1
<#
.SYNOPSIS
  One-time WEBSERVER helper: reads secrets FROM production C:\AI\ggapi\main.py (does not modify main.py),
  backs up files, writes C:\AI\ggapi\.env with production values, locks down ACL, validates python-dotenv load.

.DESCRIPTION
  This script READS hardcoded SECRET_KEY and SQL PWD from the legacy monolithic main.py on WEBSERVER.
  It does NOT swap application code or restart the API - that is a separate manual cutover.

  Re-running after Ctrl+C is safe once Phase 2 has created backups.

.NOTES
  Run ONCE on WEBSERVER as Administrator. Do NOT run on developer workstations.

.EXAMPLE
  .\scripts\migrate_secrets_to_env.ps1 -Verbose

.EXAMPLE
  .\scripts\migrate_secrets_to_env.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:ProdMain = 'C:\AI\ggapi\main.py'
$script:ProdEnv = 'C:\AI\ggapi\.env'
$script:BackupRoot = 'C:\AI\ggapi\backups'
$script:PythonExe = 'C:\ai\python\python.exe'

function Write-SummaryBox {
    param(
        [string[]]$Lines,
        [ConsoleColor]$ForegroundColor = 'White'
    )
    $w = 0
    foreach ($ln in $Lines) { if ($null -ne $ln -and $ln.Length -gt $w) { $w = $ln.Length } }
    $bar = ('-' * ([Math]::Max($w + 4, 40)))
    Write-Host $bar -ForegroundColor $ForegroundColor
    foreach ($ln in $Lines) {
        Write-Host "  $ln" -ForegroundColor $ForegroundColor
    }
    Write-Host $bar -ForegroundColor $ForegroundColor
}

function Mask-JwtSecret {
    param([string]$Secret)
    if ($null -ne $Secret) { $Secret = $Secret.Trim() }
    if ([string]::IsNullOrEmpty($Secret)) { return '(not found)' }
    if ($Secret.Length -le 8) { return '****' }
    $a = $Secret.Substring(0, [Math]::Min(4, $Secret.Length))
    $b = $Secret.Substring($Secret.Length - 4, 4)
    return "${a}...${b}"
}

function Mask-SqlPassword {
    param([string]$Pwd)
    if ($null -ne $Pwd) { $Pwd = $Pwd.Trim() }
    if ([string]::IsNullOrEmpty($Pwd)) { return '(not found)' }
    if ($Pwd.Length -le 4) { return '****' }
    $a = $Pwd.Substring(0, 2)
    $b = $Pwd.Substring($Pwd.Length - 2, 2)
    return "${a}...${b}"
}

function Parse-DotEnvFile {
    param([string]$Path)
    $ht = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $ht }
    $raw = [System.IO.File]::ReadAllText($Path)
    if ($raw.StartsWith([char]0xFEFF)) { $raw = $raw.Substring(1) }
    foreach ($line in $raw -split "`r?`n") {
        $t = $line.Trim()
        if ($t.Length -eq 0) { continue }
        if ($t.StartsWith('#')) { continue }
        $eq = $t.IndexOf('=')
        if ($eq -lt 1) { continue }
        $k = $t.Substring(0, $eq).Trim()
        $v = $t.Substring($eq + 1).Trim()
        if ($k.Length -gt 0) { $ht[$k] = $v }
    }
    return $ht
}

function Resolve-EnvExampleTemplate {
    $candidates = @(
        (Join-Path -Path $PSScriptRoot -ChildPath '.env.example'),
        (Join-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath '..') -ChildPath (Join-Path -Path 'ggapi' -ChildPath '.env.example'))
    )
    foreach ($p in $candidates) {
        try {
            $full = [System.IO.Path]::GetFullPath($p)
            if (Test-Path -LiteralPath $full) {
                Write-Verbose "Using .env.example template: $full"
                return [System.IO.File]::ReadAllText($full)
            }
        } catch { Write-Verbose "Template candidate failed: $p - $($_.Exception.Message)" }
    }
    Write-Verbose 'No .env.example on disk; using embedded fallback.'
    return @'
# ggapi/.env - fallback template (copy from repo ggapi/.env.example when available)
SQL_SERVER=localhost
SQL_DATABASE=ggpickup
SQL_USER=sa
SQL_PASSWORD=CHANGE_ME
SQL_DRIVER={ODBC Driver 17 for SQL Server}
JWT_SECRET=CHANGE_ME
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=12
PHOTO_DIR=C:\ai\ggapi\photos
SCAN_DIR=C:\ai\ggapi\scans
GOOGLE_CREDENTIALS_PATH=C:\ai\ggapi\google-credentials.json
SHEET_ID=1TSJNTWouAV1x4W6Ouh3uTKM-PDNJL9952eYqYcjoPAA
SHEET_TAB=TODAY
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
'@
}

function Build-MergedEnvContent {
    param(
        [string]$TemplateText,
        [hashtable]$Existing,
        [string]$JwtSecret,
        [string]$SqlPassword
    )
    $forced = @{
        'SQL_SERVER'   = 'localhost'
        'SQL_DATABASE' = 'ggpickup'
        'SQL_USER'     = 'sa'
        'SQL_PASSWORD' = $SqlPassword
        'JWT_SECRET'   = $JwtSecret
        'PHOTO_DIR'    = 'C:\ggphotos'
        'SCAN_DIR'     = 'C:\ggscans'
    }
    $sb = New-Object System.Text.StringBuilder
    foreach ($line in ($TemplateText -split "`r?`n")) {
        $trim = $line.TrimStart()
        if ($line.Length -eq 0) {
            [void]$sb.AppendLine('')
            continue
        }
        if ($trim.StartsWith('#')) {
            [void]$sb.AppendLine($line)
            continue
        }
        $eq = $line.IndexOf('=')
        if ($eq -lt 1) {
            [void]$sb.AppendLine($line)
            continue
        }
        $key = $line.Substring(0, $eq).Trim()
        if ($forced.ContainsKey($key)) {
            [void]$sb.AppendLine(('{0}={1}' -f $key, $forced[$key]))
        } elseif ($Existing.ContainsKey($key)) {
            [void]$sb.AppendLine(('{0}={1}' -f $key, $Existing[$key]))
        } else {
            [void]$sb.AppendLine($line)
        }
    }
    return $sb.ToString().TrimEnd("`r", "`n") + "`r`n"
}

# --- Ctrl+C: allow clean message; backups from Phase 2 make re-run safe ---
$cancelHandler = [ConsoleCancelEventHandler] {
    param([object]$sender, [ConsoleCancelEventArgs]$e)
    $e.Cancel = $true
    Write-Host ''
    Write-Host 'Interrupted (Ctrl+C). If Phase 2 finished, backups are under C:\AI\ggapi\backups - re-run is safe.' -ForegroundColor Yellow
    exit 130
}
try {
    [Console]::add_CancelKeyPress($cancelHandler)
} catch {
    Write-Verbose "Could not register CancelKeyPress handler: $($_.Exception.Message)"
}

try {
    # ========== PHASE 1 - Inspection ==========
    $wid = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $wp = New-Object System.Security.Principal.WindowsPrincipal($wid)
    if (-not $wp.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Re-run from an elevated PowerShell. Right-click PowerShell -> Run as Administrator.'
    }

    if ($env:COMPUTERNAME -ne 'WEBSERVER') {
        throw "This script must run on WEBSERVER (COMPUTERNAME is '$($env:COMPUTERNAME)')."
    }

    if (-not (Test-Path -LiteralPath $script:ProdMain)) {
        throw 'Production main.py not found at C:\AI\ggapi\main.py'
    }

    $mainText = [System.IO.File]::ReadAllText($script:ProdMain)

    $jwtMatch = [regex]::Match($mainText, 'SECRET_KEY\s*=\s*"([^"]+)"')
    if (-not $jwtMatch.Success) {
        $jwtMatch = [regex]::Match($mainText, "SECRET_KEY\s*=\s*'([^']+)'")
    }
    if (-not $jwtMatch.Success) {
        throw 'Could not find SECRET_KEY = "..." in production main.py. Fix main.py or migrate manually.'
    }
    $extractedJwt = $jwtMatch.Groups[1].Value

    $pwdMatch = [regex]::Match($mainText, 'PWD=([^;]+);')
    if (-not $pwdMatch.Success) {
        throw 'Could not find PWD=...; inside SQL connection string in production main.py.'
    }
    $extractedPwd = $pwdMatch.Groups[1].Value

    $photoHard = [regex]::Match($mainText, '(?m)^\s*PHOTO_DIR\s*=\s*(?:r)?["'']([^"'']+)["'']')
    if ($photoHard.Success) {
        $photoSummary = $photoHard.Groups[1].Value
    } else {
        $photoSummary = "not hardcoded, will use default"
    }

    $scanHard = [regex]::Match($mainText, '(?m)^\s*SCAN_DIR\s*=\s*(?:r)?["'']([^"'']+)["'']')
    if ($scanHard.Success) {
        $scanSummary = $scanHard.Groups[1].Value
    } else {
        $scanSummary = "not hardcoded, will use default"
    }

    Write-SummaryBox -ForegroundColor Yellow -Lines @(
        'PHASE 1 - Inspection summary',
        "JWT secret found: $(Mask-JwtSecret -Secret $extractedJwt)",
        "SQL password found: $(Mask-SqlPassword -Pwd $extractedPwd)",
        "Photo directory: $photoSummary",
        "Scan directory: $scanSummary"
    )

    if ($DryRun) {
        Write-Host 'DryRun complete. No changes made.' -ForegroundColor Green
        exit 0
    }

    # ========== PHASE 2 - Backup ==========
    try {
        if (-not (Test-Path -LiteralPath $script:BackupRoot)) {
            New-Item -ItemType Directory -Path $script:BackupRoot -Force | Out-Null
        }
    } catch {
        Write-Host "Failed to create backup directory: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }

    $ts = Get-Date -Format 'yyyyMMdd-HHmmss'
    $mainBak = Join-Path $script:BackupRoot "main.py.bak.$ts"
    try {
        Copy-Item -LiteralPath $script:ProdMain -Destination $mainBak -Force
    } catch {
        Write-Host "Backup of main.py failed: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }

    $envBak = $null
    if (Test-Path -LiteralPath $script:ProdEnv) {
        $envBak = Join-Path $script:BackupRoot ".env.bak.$ts"
        try {
            Copy-Item -LiteralPath $script:ProdEnv -Destination $envBak -Force
        } catch {
            Write-Host "Backup of existing .env failed: $($_.Exception.Message)" -ForegroundColor Red
            throw
        }
    }

    Write-Host 'Phase 2 backups:' -ForegroundColor Green
    Write-Host "  $mainBak" -ForegroundColor Green
    if ($envBak) { Write-Host "  $envBak" -ForegroundColor Green }

    # ========== PHASE 3 - .env preparation ==========
    $existingEnv = Parse-DotEnvFile -Path $script:ProdEnv
    $templateText = Resolve-EnvExampleTemplate
    $newContent = Build-MergedEnvContent -TemplateText $templateText -Existing $existingEnv -JwtSecret $extractedJwt -SqlPassword $extractedPwd

    try {
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($script:ProdEnv, $newContent, $utf8NoBom)
    } catch {
        Write-Host "Failed to write .env: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }

    try {
        $ic1 = & icacls $script:ProdEnv /inheritance:r 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw ("icacls inheritance:r failed (exit $LASTEXITCODE): " + ($ic1 | Out-String))
        }
    } catch {
        Write-Host "icacls /inheritance:r failed: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }

    try {
        $ic2 = & icacls $script:ProdEnv /grant:r 'SYSTEM:R' 'Administrators:R' 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw ("icacls grant failed (exit $LASTEXITCODE): " + ($ic2 | Out-String))
        }
    } catch {
        Write-Host "icacls /grant failed: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }

    Write-Host "Wrote: $script:ProdEnv (UTF-8, no BOM) - ACL restricted to SYSTEM + Administrators (read)." -ForegroundColor Green

    # ========== PHASE 4 - Validation ==========
    $pyArgs = @(
        '-c',
        "from dotenv import load_dotenv; import os; load_dotenv(r'C:\\AI\\ggapi\\.env'); print('JWT_SECRET set:', bool(os.getenv('JWT_SECRET'))); print('SQL_PASSWORD set:', bool(os.getenv('SQL_PASSWORD')))"
    )
    $pyExit = -1
    try {
        & $script:PythonExe @pyArgs
        $pyExit = $LASTEXITCODE
    } catch {
        Write-Host "Validation FAILED (python invocation threw): $($_.Exception.Message)" -ForegroundColor Red
        Write-Host 'Check C:\AI\ggapi\.env manually.' -ForegroundColor Red
        exit 1
    }

    if ($pyExit -ne 0) {
        Write-Host 'Validation FAILED. Check C:\AI\ggapi\.env manually' -ForegroundColor Red
        exit $pyExit
    }

    Write-Host '✓ .env is readable by python.' -ForegroundColor Green

    # ========== PHASE 5 - Final summary ==========
    $aclOut = ''
    try {
        $aclOut = & icacls $script:ProdEnv 2>&1 | Out-String
    } catch {
        $aclOut = "(icacls listing failed: $($_.Exception.Message))"
    }

    Write-SummaryBox -ForegroundColor Green -Lines @(
        'PHASE 5 - Cutover prep complete',
        ".env path: $script:ProdEnv",
        "Backups folder: $script:BackupRoot",
        'ACL (icacls):',
        ($aclOut.TrimEnd())
    )

    Write-SummaryBox -ForegroundColor Green -Lines @(
        'Next steps (manual - this script does NOT do these):',
        "Step 1: Stop API:    Stop-ScheduledTask -TaskName 'GG Pickup API'",
        'Step 2: Backup code: Copy-Item C:\AI\ggapi\*.py C:\AI\ggapi\backups\',
        "Step 3: Robocopy:    robocopy '<repo>\ggapi' 'C:\AI\ggapi' /E /XD __pycache__ backups OCR /XF .env google-credentials.json",
        "Step 4: Start API:   Start-ScheduledTask -TaskName 'GG Pickup API'",
        'Step 5: Smoke test:  Invoke-WebRequest http://localhost:8001/health',
        'Step 6: If anything wrong, restore main.py.bak from backups and restart task'
    )

    exit 0
} finally {
    try { [Console]::remove_CancelKeyPress($cancelHandler) } catch { }
}
