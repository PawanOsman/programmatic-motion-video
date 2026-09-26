<#
.SYNOPSIS
  Install the programmatic-motion-video skill for your coding agents, plus its Python packages.

.DESCRIPTION
  Copies this folder into the skills folder of each agent (or links it), installs the Python
  packages from requirements.txt, and checks for ffmpeg. Works in Windows PowerShell 5.1 and
  PowerShell 7 on Windows, macOS and Linux.

  If scripts are blocked, run:  powershell -ExecutionPolicy Bypass -File .\install.ps1

.EXAMPLE
  .\install.ps1                          # for the agents found here (none found: both folders below)
.EXAMPLE
  .\install.ps1 -Agent all               # ~\.claude\skills (Claude Code) and ~\.agents\skills (Codex, Gemini CLI,
                                         # Cursor, GitHub Copilot, OpenCode, Windsurf)
.EXAMPLE
  .\install.ps1 -Agent codex             # one of: claude, codex, gemini, cursor, copilot, opencode, windsurf
.EXAMPLE
  .\install.ps1 -Project .               # into a project (.claude\skills, .agents\skills)
.EXAMPLE
  .\install.ps1 -Dest D:\my-skills       # into any other skills folder
.EXAMPLE
  .\install.ps1 -Link                    # a junction to this folder instead of a copy
.EXAMPLE
  .\install.ps1 -DepsOnly -SystemDeps    # packages only, and ffmpeg through winget
.EXAMPLE
  .\install.ps1 -Uninstall
#>
[CmdletBinding()]
param(
    [string[]]$Agent = @('auto'),
    [string]$Project = '',
    [string[]]$Dest = @(),
    [switch]$Link,
    [switch]$NoDeps,
    [switch]$DepsOnly,
    [switch]$Optional,
    [switch]$SystemDeps,
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'

function Have([string]$cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function P { return [IO.Path]::Combine([string[]]$args) }         # a path from parts, with this OS's separator

$Name = 'programmatic-motion-video'
$Src = (Resolve-Path $PSScriptRoot).Path
$UserHome = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
$ConfigHome = if ($env:XDG_CONFIG_HOME) { $env:XDG_CONFIG_HOME } else { P $UserHome '.config' }

if (-not (Test-Path (P $Src 'SKILL.md'))) { throw "Run this script from the $Name folder (SKILL.md not found next to it)." }
$Version = ''
$m = Select-String -Path (P $Src 'SKILL.md') -Pattern '^\s*version:\s*"?([0-9.]+)' | Select-Object -First 1
if ($m) { $Version = $m.Matches[0].Groups[1].Value }

# ---- where each agent looks for skills ----------------------------------------------------------
function Get-HomeDir([string]$a) {
    switch ($a) {
        'claude' { return (P $UserHome '.claude' 'skills') }       # Claude Code (Copilot, OpenCode, Windsurf read it too)
        { $_ -in 'codex', 'gemini', 'cursor', 'copilot', 'opencode', 'windsurf', 'agents' } {
            return (P $UserHome '.agents' 'skills') }              # the shared Agent Skills folder all of these read
        default { throw "unknown agent: $a (use claude, codex, gemini, cursor, copilot, opencode, windsurf or all)" }
    }
}
function Get-ProjectDir([string]$a) {
    switch ($a) {
        'claude' { return (P $Project '.claude' 'skills') }
        { $_ -in 'codex', 'gemini', 'cursor', 'copilot', 'opencode', 'windsurf', 'agents' } { return (P $Project '.agents' 'skills') }
        default { throw "unknown agent: $a" }
    }
}
function Get-DetectedAgents {
    $found = @()
    if ((Test-Path (P $UserHome '.claude')) -or (Have 'claude')) { $found += 'claude' }
    $others = @('.agents', '.codex', '.gemini', '.cursor', '.copilot', (P '.codeium' 'windsurf')) |
        Where-Object { Test-Path (P $UserHome $_) }
    if ($others -or (Test-Path (P $ConfigHome 'opencode')) -or (Have 'codex') -or (Have 'gemini') -or
        (Have 'cursor-agent') -or (Have 'opencode')) { $found += 'agents' }
    if (-not $found) { $found = @('claude', 'agents') }
    return $found
}
function Get-SkillDirs([string[]]$agents) {
    $list = @($agents | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ })
    if ($list -contains 'auto') { if ($Project) { $list = @('claude', 'agents') } else { $list = Get-DetectedAgents } }
    elseif ($list -contains 'all') { $list = @('claude', 'agents') }
    $dirs = @()
    foreach ($a in $list) {
        $d = if ($Project) { Get-ProjectDir $a } else { Get-HomeDir $a }
        if ($dirs -notcontains $d) { $dirs += $d }
    }
    foreach ($d in @($Dest | ForEach-Object { $_ -split ',' })) { if ($d -and ($dirs -notcontains $d)) { $dirs += $d } }
    return $dirs
}

function Test-ThisSkill([string]$target) {
    $item = Get-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
    if (-not $item) { return $false }
    if ($item.LinkType) { return $true }
    $md = P $target 'SKILL.md'
    return ((Test-Path $md) -and (Select-String -Path $md -Pattern "^name: $Name\s*$" -Quiet))
}
function Remove-Target([string]$target) {
    $item = Get-Item -LiteralPath $target -Force
    if ($item.LinkType) { $item.Delete() }                          # the link only, never its target
    else { Remove-Item -LiteralPath $target -Recurse -Force }
}

function Install-To([string]$dir) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $dir = (Resolve-Path $dir).Path
    $target = P $dir $Name
    if ($target -eq $Src) { Write-Host "  $target (already here)"; return }
    if (Test-Path -LiteralPath $target) {
        if (-not (Test-ThisSkill $target)) { Write-Warning "skipped ${target}: a different skill with this name is there"; return }
        Remove-Target $target
    }
    if ($Link) {
        if ($IsLinux -or $IsMacOS) { New-Item -ItemType SymbolicLink -Path $target -Target $Src | Out-Null }
        else { New-Item -ItemType Junction -Path $target -Target $Src | Out-Null }   # junctions need no admin rights
        Write-Host "  linked $target -> $Src"
        return
    }
    $skip = '(^|[\\/])(\.git|dist|__pycache__)([\\/]|$)|\.pyc$|\.parts([\\/]|$)'
    Get-ChildItem -LiteralPath $Src -Recurse -Force -File | ForEach-Object {
        $rel = $_.FullName.Substring($Src.Length).TrimStart('\', '/')
        if ($rel -notmatch $skip) {
            $to = P $target $rel
            $parent = Split-Path $to -Parent
            if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
            Copy-Item -LiteralPath $_.FullName -Destination $to -Force
        }
    }
    Write-Host "  copied to $target"
}

function Uninstall-From([string]$dir) {
    $target = P $dir $Name
    if (-not (Test-Path -LiteralPath $target)) { return }
    if (-not (Test-ThisSkill $target)) { Write-Host "  left ${target}: not this skill"; return }
    $item = Get-Item -LiteralPath $target -Force
    if ((-not $item.LinkType) -and ((Resolve-Path $target).Path -eq $Src)) { Write-Host "  kept ${target}: this script runs from it"; return }
    Remove-Target $target
    Write-Host "  removed $target"
}

# ---- Python packages ----------------------------------------------------------------------------
function Invoke-Native([string]$exe, [string[]]$argv, [switch]$Quiet) {
    # Runs a program; returns its exit code. Output streams to the console unless -Quiet; the text
    # is kept in $script:NativeOut. stderr must not turn into errors under 'Stop' in PowerShell 5.1.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $script:NativeOut = @()
        & $exe @argv 2>&1 | ForEach-Object {
            $line = "$_"
            $script:NativeOut += $line
            if (-not $Quiet) { Write-Host $line }
        }
        return $LASTEXITCODE
    } catch {
        $script:NativeOut += "$_"
        return 1
    } finally { $ErrorActionPreference = $prev }
}

function Find-Python {
    foreach ($c in @(@('py', '-3'), @('python3'), @('python'))) {
        if (-not (Have $c[0])) { continue }
        $pre = @($c | Select-Object -Skip 1)
        $code = Invoke-Native $c[0] ($pre + @('-c', 'import sys; print(1 if sys.version_info >= (3, 9) else 0)')) -Quiet
        if ($code -eq 0 -and ($script:NativeOut -join '').Trim() -eq '1') { return , $c }   # not the Store stub
    }
    return $null
}

function Install-Packages($py) {
    $exe = $py[0]; $pre = @($py | Select-Object -Skip 1)
    $argv = $pre + @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', (P $Src 'requirements.txt'))
    if ($Optional) { $argv += @('-r', (P $Src 'requirements-optional.txt')) }
    if ((Invoke-Native $exe ($pre + @('-m', 'pip', '--version')) -Quiet) -ne 0) {
        Invoke-Native $exe ($pre + @('-m', 'ensurepip', '--upgrade')) -Quiet | Out-Null
    }
    if ($env:VIRTUAL_ENV -or $env:CONDA_PREFIX) { return ((Invoke-Native $exe $argv) -eq 0) }
    $code = Invoke-Native $exe ($argv + @('--user'))
    if ($code -ne 0 -and (($script:NativeOut -join ' ') -match 'externally.managed')) {
        Write-Host ''
        Write-Host 'This Python is managed by the system (PEP 668); installing for your user with --break-system-packages.'
        $code = Invoke-Native $exe ($argv + @('--user', '--break-system-packages'))
    }
    return ($code -eq 0)
}

function Show-FfmpegHelp {
    Write-Host 'Install ffmpeg (with libx264), then open a new terminal and run tools\check_env.py again:'
    Write-Host '  Windows:  winget install Gyan.FFmpeg     (or: choco install ffmpeg, scoop install ffmpeg)'
    Write-Host '  macOS:    brew install ffmpeg zbar'
    Write-Host '  Linux:    sudo apt-get install -y ffmpeg libzbar0'
    Write-Host '  or run:   .\install.ps1 -DepsOnly -SystemDeps'
}

function Install-System {
    if (Have 'winget') {
        $code = Invoke-Native 'winget' @('install', '--id', 'Gyan.FFmpeg', '-e', '--accept-source-agreements', '--accept-package-agreements')
        if ($code -eq 0) { Write-Host 'ffmpeg is installed; open a new terminal so PATH includes it.' }
        return ($code -eq 0)
    }
    if (Have 'choco') { return ((Invoke-Native 'choco' @('install', 'ffmpeg', '-y')) -eq 0) }
    if (Have 'scoop') { return ((Invoke-Native 'scoop' @('install', 'ffmpeg')) -eq 0) }
    if (Have 'brew') { return ((Invoke-Native 'brew' @('install', 'ffmpeg', 'zbar')) -eq 0) }
    if (Have 'apt-get') { return ((Invoke-Native 'sudo' @('apt-get', 'install', '-y', 'ffmpeg', 'libzbar0')) -eq 0) }
    return $false
}

# ---- run ----------------------------------------------------------------------------------------
Write-Host "programmatic-motion-video $Version"

if (-not $DepsOnly) {
    $dirs = if ($Uninstall -and ($Agent -contains 'auto') -and -not $Project -and -not $Dest) { Get-SkillDirs @('all') } else { Get-SkillDirs $Agent }
    if ($Uninstall) {
        Write-Host 'Removing the skill:'
        foreach ($d in $dirs) { Uninstall-From $d }
        return
    }
    Write-Host 'Installing the skill:'
    foreach ($d in $dirs) { Install-To $d }
}

if (-not $NoDeps -and -not $Uninstall) {
    Write-Host ''
    $py = Find-Python
    if (-not $py) {
        Write-Host 'Python 3.9 or newer was not found. Install it (winget install Python.Python.3.12, or python.org),'
        Write-Host 'then run: .\install.ps1 -DepsOnly'
        exit 1
    }
    $exe = $py[0]; $pre = @($py | Select-Object -Skip 1)
    Invoke-Native $exe ($pre + @('-c', 'import sys; print(sys.executable, sys.version.split()[0])')) -Quiet | Out-Null
    Write-Host "Installing Python packages for $($script:NativeOut -join ' '):"
    if (-not (Install-Packages $py)) {
        Write-Host 'The Python packages did not install; see the messages above.'
        exit 1
    }
    if (-not (Have 'ffmpeg')) {
        Write-Host ''
        if ($SystemDeps) {
            if (-not (Install-System)) { Show-FfmpegHelp }
        } else { Show-FfmpegHelp }
    }
    Write-Host ''
    Invoke-Native $exe ($pre + @((P $Src 'tools' 'check_env.py'), '--quick')) | Out-Null
}

if (-not $DepsOnly) {
    Write-Host ''
    Write-Host 'Done. Restart your agent (or start a new session) so it sees the skill, then ask for a video,'
    Write-Host 'for example: "Make a 30-second promo video for my app, 1080p, with music."'
}
