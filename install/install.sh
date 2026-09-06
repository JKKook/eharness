#!/usr/bin/env bash
# =====================================================================
#  eharness 설치기 — macOS · Linux · WSL2 공용   (Windows 네이티브는 install.ps1)
# =====================================================================
#  실행:  bash install/install.sh            (리포 안에서)  또는  bash ~/Downloads/install.sh  (리포 없으면 clone)
#  옵션:  --check          검증만
#         --no-service     수집기 상시 등록 생략(launchd/systemd) — 수동 기동은 /cctv-init
#  환경:  EHARNESS_REPO_URL · EHARNESS_REPO_DIR(기본 ~/tools/eharness) · EHARNESS_CLAUDE_HOME · EHARNESS_HOME · EHARNESS_PORT
#
#  하는 일: 의존성 확인 → 리포 clone/pull → ~/.local/bin/eharness 심링크 → 단위 테스트
#           → 외부 자산(install/assets: hooks/*.sh, statusline.sh → ~/.claude) + settings.json 병합
#           → eharness hooks --install → wire 5능력(init·comm·status·dispatch·probe)
#           → 수집기 상시 기동(macOS launchd / Linux systemd 유저 서비스, 없으면 안내) → 검증 8항목
#  멱등: 다시 실행해도 안전. 어느 플랫폼이든 같은 검증 항목을 같은 이름으로 보고한다.
#
#  [Claude Code 세션이 이 파일로 설치를 진행할 때]
#   · WSL2: Windows 쪽 사용자가 먼저 `wsl --install -d Ubuntu`, /etc/wsl.conf 에 [boot] systemd=true, `wsl --shutdown`.
#     Claude Code는 WSL 안에 설치·로그인(curl -fsSL https://claude.ai/install.sh | bash && claude).
#   · sudo 비밀번호를 한 번 물을 수 있다(apt). 끝나면 "검증" 블록 결과를 n/m 으로 보고한다.
# =====================================================================
set -euo pipefail

REPO_URL="${EHARNESS_REPO_URL:-https://github.com/JKKook/eharness.git}"
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "$SELF_DIR/../bin/eharness" ]; then DEFAULT_REPO="$(cd "$SELF_DIR/.." && pwd)"; else DEFAULT_REPO="$HOME/tools/eharness"; fi
REPO_DIR="${EHARNESS_REPO_DIR:-$DEFAULT_REPO}"
CLAUDE_HOME="${EHARNESS_CLAUDE_HOME:-$HOME/.claude}"
EH_HOME="${EHARNESS_HOME:-$HOME/.eharness}"
PORT="${EHARNESS_PORT:-7477}"
BIN_LINK="$HOME/.local/bin/eharness"
CAPS=(init comm status dispatch probe)
OS="$(uname -s)"
NO_SERVICE=0

log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✔\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
die()  { printf '  \033[31m✖ %s\033[0m\n' "$*" >&2; exit 1; }

# ---------- 검증 (플랫폼 공통 8항목 — install.ps1 과 같은 이름) ----------
check() {
  log "검증"
  local pass=0 total=0
  t() { local label="$1"; shift; total=$((total+1)); if "$@" >/dev/null 2>&1; then pass=$((pass+1)); ok "$label"; else warn "실패: $label"; fi; }
  t "CLI $BIN_LINK"                    test -x "$BIN_LINK"
  t "외부 자산 hooks/tool-start.sh"     test -f "$CLAUDE_HOME/hooks/tool-start.sh"
  t "settings.json: post-event.sh 훅"  python3 -c "import json,sys; d=json.load(open('$CLAUDE_HOME/settings.json')); sys.exit(0 if any('post-event.sh' in h.get('command','') for gs in d['hooks'].values() for g in gs for h in g.get('hooks',[])) else 1)"
  t "settings.json: statusLine"        python3 -c "import json,sys; d=json.load(open('$CLAUDE_HOME/settings.json')); sys.exit(0 if d.get('statusLine',{}).get('command') else 1)"
  t "스킬 cctv-init 설치"              test -f "$CLAUDE_HOME/skills/cctv-init/SKILL.md"
  t "스킬 cctv-register 설치"          test -f "$CLAUDE_HOME/skills/cctv-register/SKILL.md"
  t "에이전트 cctv-status 설치"        test -f "$CLAUDE_HOME/agents/cctv-status.md"
  t "수집기 응답 127.0.0.1:$PORT"      curl -sf -m 3 "http://127.0.0.1:$PORT/health"
  echo; echo "  결과: $pass/$total 통과"
  [ "$pass" -eq "$total" ]
}

for a in "$@"; do case "$a" in
  --check) check; exit $? ;;
  --no-service) NO_SERVICE=1 ;;
  *) die "알 수 없는 옵션: $a  (--check | --no-service)" ;;
esac; done

# ---------- 0. 의존성 ----------
log "환경: $OS"
case "$OS" in Darwin|Linux) ;; *) die "지원 안 함: $OS — Windows 네이티브는 install/install.ps1" ;; esac
grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null && ok "WSL2 감지" || true
need=(); for p in python3 curl jq git; do command -v "$p" >/dev/null 2>&1 || need+=("$p"); done
if [ ${#need[@]} -gt 0 ]; then
  if [ "$OS" = "Linux" ] && command -v apt-get >/dev/null 2>&1; then sudo apt-get update -qq && sudo apt-get install -y -qq "${need[@]}"
  elif [ "$OS" = "Darwin" ] && command -v brew >/dev/null 2>&1; then brew install "${need[@]}"
  else die "필요: ${need[*]} — 설치 후 재실행"; fi
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || die "python3 3.10 이상 필요"
ok "python3 $(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:3])))') · jq · curl · git"
command -v claude >/dev/null 2>&1 && ok "claude CLI: $(command -v claude)" || warn "claude CLI 없음 — 관제 대상이 생기려면 Claude Code 설치·로그인 필요"

# ---------- 1. 리포 + CLI ----------
log "리포: $REPO_DIR"
if [ -d "$REPO_DIR/.git" ]; then git -C "$REPO_DIR" pull --ff-only -q && ok "pull 완료"
else mkdir -p "$(dirname "$REPO_DIR")" && git clone -q "$REPO_URL" "$REPO_DIR" && ok "clone 완료"; fi
mkdir -p "$HOME/.local/bin"; ln -sfn "$REPO_DIR/bin/eharness" "$BIN_LINK"
chmod +x "$REPO_DIR/bin/eharness" "$REPO_DIR"/hooks/*.sh "$REPO_DIR"/scaffold/skills/*/*.sh
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *)
  rc="$HOME/.bashrc"; [ "$OS" = "Darwin" ] && rc="$HOME/.zshrc"
  grep -q '\.local/bin' "$rc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
  export PATH="$HOME/.local/bin:$PATH"; warn "PATH에 ~/.local/bin 추가($rc) — 새 셸부터 적용";;
esac
ok "eharness $("$BIN_LINK" --version)"

log "단위 테스트"
(cd "$REPO_DIR" && python3 -m unittest discover -s tests 2>&1 | grep -E "^(Ran|OK|FAILED)" | sed 's/^/  /'; test "${PIPESTATUS[0]}" = 0) || warn "테스트 실패 — 검증 결과와 함께 보고"

# ---------- 2. 외부 자산 + settings.json ----------
log "외부 자산 → $CLAUDE_HOME (hooks/*.sh, statusline.sh)"
mkdir -p "$CLAUDE_HOME/hooks" "$CLAUDE_HOME/hook-state" "$EH_HOME"
cp "$REPO_DIR"/install/assets/hooks/*.sh "$CLAUDE_HOME/hooks/"
cp "$REPO_DIR/install/assets/statusline.sh" "$CLAUDE_HOME/statusline.sh"
chmod +x "$CLAUDE_HOME"/hooks/*.sh "$CLAUDE_HOME/statusline.sh"
ok "$(ls "$REPO_DIR"/install/assets/hooks | tr '\n' ' ')statusline.sh"
python3 "$REPO_DIR/install/merge_settings.py" "$CLAUDE_HOME/settings.json" "$REPO_DIR/install/assets/settings-snippet.json" | sed 's/^/  /'

# ---------- 3. 배선 ----------
log "eharness hooks --install (관측 훅)"
"$BIN_LINK" hooks --install --port "$PORT" | sed 's/^/  /'
log "wire: ${CAPS[*]}"
for c in "${CAPS[@]}"; do "$BIN_LINK" wire "$c" --install >/dev/null && ok "wire $c" || warn "wire $c 실패"; done

# ---------- 4. 수집기 상시 기동 ----------
if [ "$NO_SERVICE" = 1 ]; then log "수집기 상시 등록 생략(--no-service)"
elif [ "$OS" = "Darwin" ]; then
  log "수집기: launchd"; "$BIN_LINK" collect --install --port "$PORT" | sed 's/^/  /'
elif command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
  log "수집기: systemd 유저 서비스 eharness-collect"
  mkdir -p "$HOME/.config/systemd/user"
  cat > "$HOME/.config/systemd/user/eharness-collect.service" <<EOF
[Unit]
Description=eharness collector (127.0.0.1:$PORT)
[Service]
ExecStart=$(command -v python3) $REPO_DIR/bin/eharness collect --port $PORT
Restart=always
RestartSec=2
StandardOutput=append:$EH_HOME/collect.log
StandardError=append:$EH_HOME/collect.log
[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload && systemctl --user enable --now eharness-collect && systemctl --user restart eharness-collect
  loginctl enable-linger "$USER" 2>/dev/null || true
  ok "등록·기동 (로그 $EH_HOME/collect.log)"
else
  log "수집기: systemd 유저 세션 없음 → nohup 기동"; warn "WSL이면 /etc/wsl.conf 에 systemd=true 후 wsl --shutdown, 재실행하면 서비스로 등록됨"
  bash "$REPO_DIR/scaffold/skills/cctv-init/init.sh" start --port "$PORT" | sed 's/^/  /' || true
fi
for _ in $(seq 1 20); do curl -sf -m 1 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break; sleep 0.5; done   # 재기동 대기(최대 10s)

# ---------- 5. 검증 ----------
check || true
cat <<EOF

  다음: 새 터미널에서 claude 세션을 열고  eharness ps  또는 브라우저  http://127.0.0.1:$PORT/
        세션 안: "cctv 켜"(cctv-init) · "다른 세션들 뭐 해?"(cctv-status) · "cctv 등록 리더 <이름>"(cctv-register)
EOF
