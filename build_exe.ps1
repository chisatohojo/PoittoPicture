$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$appVersion = "0.1.0"
$exeName = "poitto-picture"
$packageName = "poitto-picture_v$($appVersion)_windows"
$distDir = Join-Path $projectRoot "dist"
$packageDir = Join-Path $distDir $packageName
$zipPath = Join-Path $distDir "$packageName.zip"
$iconPath = Join-Path $projectRoot "assets\app_icon.ico"
$entryPath = Join-Path $projectRoot "poitto_picture.py"

function Assert-InsideDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [Parameter(Mandatory = $true)][string]$ParentPath
    )

    $parentFullPath = [System.IO.Path]::GetFullPath($ParentPath).TrimEnd('\')
    $targetFullPath = [System.IO.Path]::GetFullPath($TargetPath).TrimEnd('\')

    if (-not $targetFullPath.StartsWith($parentFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe path outside expected directory: $targetFullPath"
    }
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    python -m venv .venv
}

Invoke-Checked { & $python -m pip install --upgrade pip }
Invoke-Checked { & $python -m pip install -r requirements.txt }

New-Item -ItemType Directory -Force -Path $distDir | Out-Null

Invoke-Checked { & $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name $exeName `
    --icon $iconPath `
    --add-data "$iconPath;assets" `
    --specpath "build" `
    $entryPath }

if (Test-Path $packageDir) {
    Assert-InsideDirectory -TargetPath $packageDir -ParentPath $distDir
    Remove-Item -LiteralPath $packageDir -Recurse -Force
}

if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

New-Item -ItemType Directory -Force -Path $packageDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $packageDir "assets") | Out-Null

Copy-Item -LiteralPath (Join-Path $distDir "$exeName.exe") -Destination (Join-Path $packageDir "$exeName.exe")
Copy-Item -LiteralPath (Join-Path $projectRoot "README.txt") -Destination (Join-Path $packageDir "README.txt")
Copy-Item -LiteralPath (Join-Path $projectRoot "LICENSE.txt") -Destination (Join-Path $packageDir "LICENSE.txt")
Copy-Item -LiteralPath (Join-Path $projectRoot "CHANGELOG.txt") -Destination (Join-Path $packageDir "CHANGELOG.txt")
Copy-Item -LiteralPath $iconPath -Destination (Join-Path $packageDir "assets\icon.ico")

Compress-Archive -LiteralPath $packageDir -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host ""
Write-Host "Build complete:"
Write-Host "  EXE: $distDir\$exeName.exe"
Write-Host "  ZIP: $zipPath"
