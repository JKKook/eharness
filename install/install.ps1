<#
=====================================================================
 eharness 설치기 — Windows 네이티브(PowerShell)   (macOS · Linux · WSL2 는 install/install.sh)
=====================================================================
 실행:  & install\install.ps1  (리포 안에서)  또는  & ~\Downloads\install.ps1  (리포 없으면 clone)

 [Claude Code 세션이 이 파일을 받았을 때 따라야 할 절차]

 0. 실행 환경: Windows PowerShell 5.1 또는 PowerShell 7. 관리자 권한 불필요(현재 사용자 범위만 변경).
    선행 조건(없으면 사용자에게 설치를 안내하고 중단):
      · Git for Windows  — Claude Code Windows 네이티브의 필수 요건이자, 훅·스킬 스크립트(.sh)를 실행하는 Git Bash 제공
      · Python 3.10+     — https://www.python.org (설치 시 "Add python.exe to PATH" 체크)
      · Claude Code       — 로그인까지 완료:  irm https://claude.ai/install.ps1 | iex  →  claude
 1. 실행:
      Set-ExecutionPolicy -Scope Process Bypass -Force
      & "$HOME\Downloads\eharness-windows-install.ps1"
    · 멱등: 다시 실행해도 안전(리포 pull, settings.json 병합은 중복 없이 갱신).
    · 검증만:  & ".\eharness-windows-install.ps1" -Check
 2. 끝나면 마지막 "검증" 블록의 결과(n/m 통과)를 사용자에게 보고한다.
 3. 이후 세션 안에서 "cctv 켜"(cctv-init) / "다른 세션들 뭐 해?"(cctv-status) 로 사용. 대시보드 http://127.0.0.1:7477/

 [하는 일]  선행 조건 확인(+jq 는 winget 으로 시도) → 리포 clone/pull(~\tools\eharness) → eharness.cmd 심(~\.local\bin, 사용자 PATH)
           → 사용자 환경변수 EHARNESS_BIN(Git Bash 스킬용) → 단위 테스트 → 외부 자산(install/assets → ~\.claude, jq 있을 때만)
           → settings.json 병합 → eharness hooks --install → wire 5능력(init·comm·status·dispatch·probe)
           → 수집기 로그온 작업 스케줄러 등록(launchd/systemd 대체)·즉시 기동 → 검증 8항목(install.sh 와 같은 이름)

 [리포 쪽 전제]  2026-09-06 Windows 호환 패치가 포함된 리포여야 한다(registry.alive 핸들 조회, 슬러그 \ : 처리,
           훅 슬래시 경로, getuid 가드, wire의 Git Bash 탐색). 이전 버전은 Windows에서 os.kill(pid,0)이
           세션을 종료시키므로 절대 실행하지 말 것.

 [네이티브 제약]
   · 외부 자산(hooks/*.sh·statusline.sh)은 jq 가 있어야 설치(없으면 생략·검증 2항목 실패로 표시). 생략 시 "지금 실행 중 도구" 비어 있음, ctx 근사치(~).
   · 터미널 컬럼(ps -E)·cmux 트리 — macOS 전용. 대시보드는 "표" 모드로.
   · cctv-register 의 프로세스 트리 해석(ps -o)은 Git Bash 미검증.
   · 수집기 로그 — pythonw 로 창 없이 돌아 stdout 없음. 상태는 http://127.0.0.1:7477/health 로 확인.
=====================================================================
#>
[CmdletBinding()]
param(
  [switch]$Check,
  [int]$Port = 7477,
  [string]$RepoUrl = "https://github.com/JKKook/eharness.git",
  [string]$RepoDir = $(if ($PSScriptRoot -and (Test-Path "$PSScriptRoot\..\bin\eharness")) { (Resolve-Path "$PSScriptRoot\..").Path } else { "$HOME\tools\eharness" })
)
$ErrorActionPreference = "Stop"
$ClaudeHome = if ($env:EHARNESS_CLAUDE_HOME) { $env:EHARNESS_CLAUDE_HOME } else { "$HOME\.claude" }
$EhHome     = if ($env:EHARNESS_HOME) { $env:EHARNESS_HOME } else { "$HOME\.eharness" }
$BinDir     = "$HOME\.local\bin"
$Shim       = "$BinDir\eharness.cmd"
$TaskName   = "eharness-collect"
$Caps       = @("init", "comm", "status", "dispatch", "probe")
$Api        = "http://127.0.0.1:$Port"

function Log($m)  { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  [!]  $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "  [X]  $m" -ForegroundColor Red; exit 1 }

function Find-GitBash {
  $c = @("C:\Program Files\Git\bin\bash.exe", "C:\Program Files\Git\usr\bin\bash.exe", "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe")
  $git = Get-Command git -ErrorAction SilentlyContinue
  if ($git) { $c += (Join-Path (Split-Path (Split-Path $git.Source)) "bin\bash.exe") }
  foreach ($p in $c) { if (Test-Path $p) { return $p } }
  return $null
}
function Find-Python {
  foreach ($cand in @(@{ Cmd = "py"; Pre = @("-3") }, @{ Cmd = "python"; Pre = @() }, @{ Cmd = "python3"; Pre = @() })) {
    if (-not (Get-Command $cand.Cmd -ErrorAction SilentlyContinue)) { continue }
    $pre = $cand.Pre
    try { $v = (& $cand.Cmd @pre -c "import sys;print('%d.%d.%d'%sys.version_info[:3])" 2>$null | Select-Object -First 1) } catch { continue }
    if ($v -and ([version]$v) -ge [version]"3.10") {
      $exe = (& $cand.Cmd @pre -c "import sys;print(sys.executable)" | Select-Object -First 1)
      return @{ Cmd = $cand.Cmd; Pre = $pre; Ver = $v; Exe = $exe; Bash = (@($cand.Cmd) + $pre) -join " " }
    }
  }
  return $null
}
function Invoke-Py { param([string[]]$A) $pre = $script:Py.Pre; & $script:Py.Cmd @pre @A }

# ---------- 검증 (-Check 로 단독 실행 가능) ----------
function Test-Install {
  Log "검증"
  $script:pass = 0; $script:total = 0
  function T($label, [scriptblock]$cond) {
    $script:total++
    $r = $false; try { $r = [bool](& $cond) } catch { $r = $false }
    if ($r) { $script:pass++; Ok $label } else { Warn "실패: $label" }
  }
  T "CLI $Shim"                         { Test-Path $Shim }
  T "외부 자산 hooks/tool-start.sh"     { Test-Path "$ClaudeHome\hooks\tool-start.sh" }
  T "settings.json: post-event.sh 훅"   { (Get-Content "$ClaudeHome\settings.json" -Raw) -match "eharness/hooks/post-event\.sh" }
  T "settings.json: statusLine"         { (Get-Content "$ClaudeHome\settings.json" -Raw | ConvertFrom-Json).statusLine.command }
  T "스킬 cctv-init 설치"               { Test-Path "$ClaudeHome\skills\cctv-init\SKILL.md" }
  T "스킬 cctv-register 설치"           { Test-Path "$ClaudeHome\skills\cctv-register\SKILL.md" }
  T "에이전트 cctv-status 설치"         { Test-Path "$ClaudeHome\agents\cctv-status.md" }
  T "수집기 응답 127.0.0.1:$Port"       { (Invoke-RestMethod -Uri "$Api/health" -TimeoutSec 3).ok }
  Write-Host "`n  결과: $script:pass/$script:total 통과"
  return ($script:pass -eq $script:total)
}
if ($Check) { if (Test-Install) { exit 0 } else { exit 1 } }

# ---------- 0. 선행 조건 ----------
Log "선행 조건"
if (-not $IsWindows -and $PSVersionTable.PSEdition -eq "Core" -and $env:OS -ne "Windows_NT") { Die "Windows 에서만 실행. WSL/리눅스는 eharness-wsl-install.sh 사용" }
$Bash = Find-GitBash; if (-not $Bash) { Die "Git for Windows(Git Bash) 없음 — https://git-scm.com/download/win 설치 후 재실행" }; Ok "Git Bash: $Bash"
$Py = Find-Python;    if (-not $Py)   { Die "Python 3.10+ 없음 — https://www.python.org 설치(PATH 추가 체크) 후 재실행" }; Ok "Python $($Py.Ver): $($Py.Exe)"
if (-not (Get-Command jq -ErrorAction SilentlyContinue)) {
  Warn "jq 없음 — winget 으로 설치 시도(외부 자산 statusline·tool-start 훅에 필요)"
  try { winget install -e --id jqlang.jq --silent --accept-source-agreements --accept-package-agreements | Out-Null } catch {}
  $env:PATH = "$env:LOCALAPPDATA\Microsoft\WinGet\Links;$env:PATH"
}
if (Get-Command jq -ErrorAction SilentlyContinue) { Ok "jq: $((Get-Command jq).Source)" } else { Warn "jq 여전히 없음 — 외부 자산 설치 생략(검증 2항목 실패로 표시됨)" }
if (Get-Command claude -ErrorAction SilentlyContinue) { Ok "claude CLI: $((Get-Command claude).Source)" } else { Warn "claude CLI 없음 — 관제 대상이 생기려면 Claude Code 설치·로그인 필요" }
$env:PATH = "$(Split-Path $Bash);$env:PATH"   # 이 프로세스에서만: 테스트·wire 검증이 bash 를 찾도록

# ---------- 1. 리포 ----------
Log "리포: $RepoDir"
if (Test-Path "$RepoDir\.git") { git -C $RepoDir pull --ff-only | Out-Null; Ok "pull 완료" }
else { New-Item -ItemType Directory -Force (Split-Path $RepoDir) | Out-Null; git clone $RepoUrl $RepoDir | Out-Null; Ok "clone 완료" }
if (-not (Select-String -Path "$RepoDir\cctv\sources\registry.py" -Pattern "OpenProcess" -Quiet)) { Die "리포에 Windows 호환 패치가 없음(registry.alive) — 이 버전은 Windows 에서 세션을 종료시킬 수 있어 중단" }
$RepoFwd = $RepoDir -replace "\\", "/"

# ---------- 2. CLI 심 + PATH + EHARNESS_BIN ----------
Log "CLI 심 $Shim"
New-Item -ItemType Directory -Force $BinDir, $EhHome | Out-Null
"@echo off`r`n`"$($Py.Exe)`" `"$RepoDir\bin\eharness`" %*" | Set-Content -Path $Shim -Encoding ASCII
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ";") -notcontains $BinDir) { [Environment]::SetEnvironmentVariable("Path", (@($userPath, $BinDir) | Where-Object { $_ }) -join ";", "User"); Warn "사용자 PATH 에 $BinDir 추가 — 새 터미널부터 적용" }
$env:PATH = "$BinDir;$env:PATH"
$binVal = "$($Py.Bash) $RepoFwd/bin/eharness"   # 따옴표 없이(init.sh 가 단어 분리로 실행) — 경로에 공백이 있으면 EHARNESS_BIN 을 수동 조정
[Environment]::SetEnvironmentVariable("EHARNESS_BIN", $binVal, "User"); $env:EHARNESS_BIN = $binVal
Ok "EHARNESS_BIN=$binVal  (Git Bash 스킬 init.sh 가 사용)"
Ok ("eharness " + (Invoke-Py @("$RepoDir\bin\eharness", "--version")))

Log "단위 테스트"
Push-Location $RepoDir
$eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"   # unittest 는 stderr 로 출력 — 5.1 에서 예외로 오인되지 않게
$out = Invoke-Py @("-m", "unittest", "discover", "-s", "tests") 2>&1 | ForEach-Object { "$_" }
$ErrorActionPreference = $eap
$out | Select-Object -Last 3 | ForEach-Object { "  $_" }
if ($LASTEXITCODE -ne 0) { Warn "테스트 실패 항목 있음 — 아래 검증 결과와 함께 보고" }
Pop-Location

# ---------- 2b. 외부 자산(jq 있을 때만) + settings.json 병합 ----------
Log "외부 자산 → $ClaudeHome"
New-Item -ItemType Directory -Force "$ClaudeHome\hooks", "$ClaudeHome\hook-state" | Out-Null
if (Get-Command jq -ErrorAction SilentlyContinue) {
  Copy-Item "$RepoDir\install\assets\hooks\*.sh" "$ClaudeHome\hooks\" -Force
  Copy-Item "$RepoDir\install\assets\statusline.sh" "$ClaudeHome\statusline.sh" -Force
  Invoke-Py @("$RepoDir\install\merge_settings.py", "$ClaudeHome\settings.json", "$RepoDir\install\assets\settings-snippet.json") | ForEach-Object { "  $_" }
  Ok "hooks/*.sh · statusline.sh (sh=Git Bash 로 실행)"
} else { Warn "jq 없음 — 외부 자산·statusLine 생략" }

# ---------- 3. 배선 ----------
Log "eharness hooks --install (post-event.sh 관측 훅, sh=Git Bash 로 실행됨)"
Invoke-Py @("$RepoDir\bin\eharness", "hooks", "--install", "--port", "$Port")
Log "wire: $($Caps -join ' ')"
foreach ($c in $Caps) { try { Invoke-Py @("$RepoDir\bin\eharness", "wire", $c, "--install"); Ok "wire $c" } catch { Warn "wire $c 실패: $_" } }

# ---------- 4. 수집기 상시 기동 (launchd/systemd 대체: 로그온 작업) ----------
Log "수집기 로그온 작업: $TaskName"
$pyw = $Py.Exe -replace "python\.exe$", "pythonw.exe"; if (-not (Test-Path $pyw)) { $pyw = $Py.Exe }
try {
  $action   = New-ScheduledTaskAction -Execute $pyw -Argument "`"$RepoDir\bin\eharness`" collect --port $Port" -WorkingDirectory $RepoDir
  $trigger  = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
  $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -StartWhenAvailable
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
  Ok "작업 등록 (로그온 시 자동 기동, 무한 실행)"
  try { Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue } catch {}
  Start-ScheduledTask -TaskName $TaskName; Ok "지금 기동"
} catch {
  Warn "작업 스케줄러 등록 실패($_) — 시작 프로그램 폴더로 대체"
  $startup = [Environment]::GetFolderPath("Startup"); $cmd = "$startup\eharness-collect.cmd"
  "@echo off`r`nstart `"`" /min `"$pyw`" `"$RepoDir\bin\eharness`" collect --port $Port" | Set-Content -Path $cmd -Encoding ASCII
  Start-Process -FilePath $pyw -ArgumentList "`"$RepoDir\bin\eharness`" collect --port $Port" -WindowStyle Hidden
  Ok "시작 프로그램: $cmd (+ 지금 기동)"
}
Start-Sleep -Seconds 3

# ---------- 5. 검증 ----------
$null = Test-Install
Write-Host @"

  다음 단계:
   · 새 터미널에서 claude 세션을 하나 열고  eharness ps  또는 브라우저에서  $Api/  확인
   · 세션 안: "cctv 켜" (cctv-init) · "다른 세션들 뭐 해?" (cctv-status) · "cctv 등록 리더 <이름>" (cctv-register)
   · 셸:      eharness ps | watch 3 | events -f | hooks | wire comm --status | doctor
   · 수집기:  Get-ScheduledTask $TaskName | Start-ScheduledTask $TaskName | Stop-ScheduledTask $TaskName
   · 검증만:  & install\install.ps1 -Check
"@
exit 0
