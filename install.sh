#!/usr/bin/env bash
# meegle-buddy installer — pretty one-liner setup
#   curl -fsSL https://raw.githubusercontent.com/thanathe/meegle-buddy/main/install.sh | bash
# Flags:  --dry-run   print what would run, change nothing
set -euo pipefail

DRY_RUN=false
[ "${1:-}" = "--dry-run" ] && DRY_RUN=true

# ── colors (fall back to plain when not a tty / NO_COLOR) ────────────────────
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  B=$'\033[1m'; DIM=$'\033[2m'; R=$'\033[0m'
  CY=$'\033[38;5;51m'; MG=$'\033[38;5;213m'; GR=$'\033[38;5;114m'; YL=$'\033[38;5;222m'; RD=$'\033[38;5;203m'
else
  B=""; DIM=""; R=""; CY=""; MG=""; GR=""; YL=""; RD=""
fi

step()  { printf '%s\n' "${CY}◆${R} ${B}$1${R}"; }
ok()    { printf '%s\n' "${GR}✔${R} $1"; }
warn()  { printf '%s\n' "${YL}▲${R} $1"; }
fail()  { printf '%s\n' "${RD}✖${R} $1"; }
runcmd(){ if $DRY_RUN; then printf '%s\n' "${DIM}  (dry-run) $*${R}"; else "$@"; fi; }

# ── banner ────────────────────────────────────────────────────────────────────
printf '\n'
printf '%s\n' "${MG}   ╭──────────────────────────────────────────────╮${R}"
printf '%s\n' "${MG}   │${R}                                              ${MG}│${R}"
printf '%s\n' "${MG}   │${R}   ${B}🐣  m e e g l e - b u d d y${R}                ${MG}│${R}"
printf '%s\n' "${MG}   │${R}   ${DIM}your friendly Meegle sidekick${R}              ${MG}│${R}"
printf '%s\n' "${MG}   │${R}                                              ${MG}│${R}"
printf '%s\n' "${MG}   │${R}   ${DIM}cards · timelog · schedule — no field${R}      ${MG}│${R}"
printf '%s\n' "${MG}   │${R}   ${DIM}IDs, everything discovered for you${R}         ${MG}│${R}"
printf '%s\n' "${MG}   │${R}                                              ${MG}│${R}"
printf '%s\n' "${MG}   ╰──────────────────────────────────────────────╯${R}"
printf '\n'

# ── 1/3 prerequisites ────────────────────────────────────────────────────────
step "1/3  Checking prerequisites"
if command -v npx >/dev/null 2>&1; then
  ok "node/npx found ($(node --version 2>/dev/null || echo '?'))"
else
  fail "npx not found — install Node.js first: https://nodejs.org"
  exit 1
fi

# ── 2/3 install the skill ────────────────────────────────────────────────────
step "2/3  Installing the meegle-buddy skill (global, all agents)"
runcmd npx -y skills@latest add thanathe/meegle-buddy -g -y
ok "skill installed — your agent now knows Meegle"

# ── 3/3 meegle CLI ───────────────────────────────────────────────────────────
step "3/3  Checking the meegle CLI"
if command -v meegle >/dev/null 2>&1; then
  ok "meegle CLI found (v$(meegle version 2>/dev/null || echo '?'))"
  if meegle auth status --format json 2>/dev/null | grep -q '"authenticated": *true'; then
    ok "already logged in"
  else
    warn "not logged in — run:  ${B}meegle auth login --device-code${R}"
  fi
else
  warn "meegle CLI not installed — run the official one-stop wizard:"
  printf '%s\n' "    ${B}npx @lark-project/meegle@latest install${R}"
fi

# ── done ─────────────────────────────────────────────────────────────────────
printf '\n'
printf '%s\n' "${GR}${B}  พร้อมใช้แล้วครับ! 🎉${R}"
printf '%s\n' "  ${DIM}ลองพิมพ์กับ agent ของคุณ:${R}  ${B}\"ลงเวลาวันนี้หน่อย\"${R}  ${DIM}หรือ${R}  ${B}\"เปิดการ์ดใหม่\"${R}"
printf '%s\n' "  ${DIM}ครั้งแรก skill จะพาสำรวจ space ของคุณเองอัตโนมัติ (init)${R}"
printf '\n'
