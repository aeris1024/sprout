<#
.SYNOPSIS
Sprout CLIをインストールし、GUIをビルドしてインストールします。

.DESCRIPTION
リポジトリのルートで実行します。再実行すると、現在のコードでCLIとGUIを更新します。
GUIはユーザー単位のNSISインストーラーで導入するため、管理者権限は不要です。

.PARAMETER CliOnly
CLIだけをインストールします。GUIのビルドとインストールは行いません。

.PARAMETER BuildOnly
CLIをインストールし、GUIのインストーラーを作成するところで止めます。

.EXAMPLE
.\scripts\install.ps1
.\scripts\install.ps1 -CliOnly
.\scripts\install.ps1 -BuildOnly
#>
[CmdletBinding()]
param(
    [switch]$CliOnly,
    [switch]$BuildOnly
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$gui = Join-Path $root 'gui'

function Write-Step([string]$message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Invoke-Native([string]$command, [string[]]$arguments, [string]$workingDirectory = $root) {
    Push-Location $workingDirectory
    try {
        & $command @arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$command $($arguments -join ' ') が終了コード $LASTEXITCODE で失敗しました。"
        }
    }
    finally {
        Pop-Location
    }
}

function Assert-Tools([hashtable[]]$tools) {
    $missing = @($tools | Where-Object { -not (Get-Command $_.Name -ErrorAction SilentlyContinue) })
    if ($missing.Count -eq 0) {
        return
    }
    Write-Host ""
    Write-Host "必要なツールが見つかりません。導入してからターミナルを開き直し、再実行してください。" -ForegroundColor Red
    foreach ($tool in $missing) {
        Write-Host ("  - {0}: {1}" -f $tool.Name, $tool.Hint)
    }
    exit 1
}

$required = @(@{ Name = 'uv'; Hint = 'https://docs.astral.sh/uv/getting-started/installation/' })
if (-not $CliOnly) {
    $required += @(
        @{ Name = 'node'; Hint = 'Node.js 20.19以降 https://nodejs.org/' },
        @{ Name = 'pnpm'; Hint = 'npm install -g pnpm' },
        @{ Name = 'cargo'; Hint = 'Rust stable（MSVC） https://rustup.rs/ とVisual Studio 2022のC++ビルドツール' }
    )
}
Assert-Tools $required

Write-Step 'Sprout CLIをインストールしています'
# --reinstall rebuilds from the current checkout even when the version number is unchanged.
Invoke-Native 'uv' @('tool', 'install', '--force', '--reinstall', '--quiet', '.')
$bin = (& uv tool dir --bin).Trim()
$sprout = Join-Path $bin 'sprout.exe'
Invoke-Native $sprout @('--version')
$pathEntries = @($env:Path -split ';' | Where-Object { $_ } | ForEach-Object { $_.TrimEnd('\') })
if ($pathEntries -notcontains $bin.TrimEnd('\')) {
    Write-Warning "$bin がPATHにありません。'uv tool update-shell' を実行してターミナルを開き直すと、sprout コマンドとGUIからCLIを使えます。"
}

if ($CliOnly) {
    Write-Step '完了しました（CLIのみ）'
    exit 0
}

Write-Step 'GUIの依存パッケージを準備しています'
Invoke-Native 'pnpm' @('install', '--frozen-lockfile') $gui

Write-Step 'GUIをビルドしています（初回は数分かかります）'
Invoke-Native 'pnpm' @('tauri', 'build', '--bundles', 'nsis') $gui

$bundle = Join-Path $gui 'src-tauri\target\release\bundle\nsis'
$installer = Get-ChildItem -Path $bundle -Filter '*-setup.exe' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $installer) {
    throw "GUIのインストーラーが $bundle に見つかりません。"
}

if ($BuildOnly) {
    Write-Step '完了しました（インストーラーの作成まで）'
    Write-Host "インストーラー: $($installer.FullName)"
    exit 0
}

Write-Step 'GUIをインストールしています'
# /S installs silently for the current user and replaces an earlier installation.
$process = Start-Process -FilePath $installer.FullName -ArgumentList '/S' -Wait -PassThru
if ($process.ExitCode -ne 0) {
    throw "GUIのインストーラーが終了コード $($process.ExitCode) で失敗しました。Sproutを終了してから再実行してください。"
}

Write-Step '完了しました'
Write-Host 'スタートメニューの「Sprout」からGUIを起動できます。CLIは sprout コマンドで使えます。'
