#!/usr/bin/env bash
# Install the programmatic-motion-video skill for your coding agents, plus its Python packages.
#
#   ./install.sh                        for the agents found here (none found: ~/.claude/skills and ~/.agents/skills)
#   ./install.sh --agent all            ~/.claude/skills (Claude Code) and ~/.agents/skills (Codex, Gemini CLI,
#                                       Cursor, GitHub Copilot, OpenCode, Windsurf)
#   ./install.sh --agent codex          one of: claude codex gemini cursor copilot opencode windsurf
#   ./install.sh --project .            into a project (.claude/skills, .agents/skills) instead of your home
#   ./install.sh --dest DIR             into any other skills folder (repeatable)
#   ./install.sh --link                 symlink to this folder instead of copying (to develop the skill)
#   ./install.sh --no-deps              skill files only        --deps-only   packages only
#   ./install.sh --optional             also QR decoding, PDF artwork, code highlighting, web capture
#   ./install.sh --system-deps          also install ffmpeg, zbar (and GL libraries on Linux) with the system package manager
#   ./install.sh --uninstall            remove the installed copies
set -euo pipefail

NAME=programmatic-motion-video
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
AGENTS=auto
PROJECT=""
EXTRA_DESTS=""
LINK=0
DEPS=1
SKILLS=1
OPTIONAL=0
SYSDEPS=auto
UNINSTALL=0

usage() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$SRC/install.sh"; }
have() { command -v "$1" >/dev/null 2>&1; }
say() { printf '%s\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --agent|--agents) AGENTS="${2:?--agent needs a value}"; shift 2 ;;
    --agent=*|--agents=*) AGENTS="${1#*=}"; shift ;;
    --project) PROJECT="${2:?--project needs a folder}"; shift 2 ;;
    --project=*) PROJECT="${1#*=}"; shift ;;
    --dest) EXTRA_DESTS="$EXTRA_DESTS
${2:?--dest needs a folder}"; shift 2 ;;
    --dest=*) EXTRA_DESTS="$EXTRA_DESTS
${1#*=}"; shift ;;
    --link) LINK=1; shift ;;
    --no-deps) DEPS=0; shift ;;
    --deps-only) SKILLS=0; shift ;;
    --optional) OPTIONAL=1; shift ;;
    --system-deps) SYSDEPS=yes; shift ;;
    --no-system-deps) SYSDEPS=no; shift ;;
    --uninstall) UNINSTALL=1; DEPS=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) say "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -f "$SRC/SKILL.md" ] || { say "run this script from the $NAME folder (SKILL.md not found next to it)" >&2; exit 1; }
VERSION="$(sed -n 's/^ *version: *"\{0,1\}\([0-9.]*\)"\{0,1\}.*/\1/p' "$SRC/SKILL.md" | head -n 1)"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

# ---- where each agent looks for skills -------------------------------------------------------
home_dir_for() {
  case "$1" in
    claude) say "$HOME/.claude/skills" ;;                  # Claude Code (Copilot, OpenCode and Windsurf read it too)
    codex|gemini|cursor|copilot|opencode|windsurf|agents)
            say "$HOME/.agents/skills" ;;                  # the shared Agent Skills folder all of these read
    *) return 1 ;;
  esac
}
project_dir_for() {
  case "$1" in
    claude) say "$PROJECT/.claude/skills" ;;
    codex|gemini|cursor|copilot|opencode|windsurf|agents) say "$PROJECT/.agents/skills" ;;
    *) return 1 ;;
  esac
}
detect_agents() {
  local found=""
  if [ -d "$HOME/.claude" ] || have claude; then found="$found claude"; fi
  if [ -d "$HOME/.agents" ] || [ -d "$HOME/.codex" ] || [ -d "$HOME/.gemini" ] || [ -d "$HOME/.cursor" ] \
     || [ -d "$HOME/.copilot" ] || [ -d "$CONFIG_HOME/opencode" ] || [ -d "$HOME/.codeium/windsurf" ] \
     || have codex || have gemini || have cursor-agent || have opencode; then found="$found agents"; fi
  [ -n "$found" ] || found="claude agents"
  say "$found"
}

skill_dirs() {  # one folder per line, without duplicates
  local list agent dir out=""
  if [ "$AGENTS" = auto ]; then
    if [ -n "$PROJECT" ]; then list="claude agents"; else list="$(detect_agents)"; fi
  elif [ "$AGENTS" = all ]; then
    list="claude agents"
  else
    list="$(printf '%s' "$AGENTS" | tr ',' ' ')"
  fi
  for agent in $list; do
    if [ -n "$PROJECT" ]; then dir="$(project_dir_for "$agent")" || { say "unknown agent: $agent" >&2; exit 2; }
    else dir="$(home_dir_for "$agent")" || { say "unknown agent: $agent" >&2; exit 2; }; fi
    case "$out" in *"|$dir|"*) ;; *) out="$out|$dir|" ;; esac
  done
  printf '%s' "$out" | tr '|' '\n' | sed '/^$/d'
  if [ -n "$EXTRA_DESTS" ]; then printf '%s\n' "$EXTRA_DESTS" | sed '/^$/d'; fi
}

is_this_skill() { [ -L "$1" ] || grep -q "^name: $NAME\$" "$1/SKILL.md" 2>/dev/null; }

install_to() {
  local dir="$1" target real
  mkdir -p "$dir"
  dir="$(cd "$dir" && pwd -P)"
  target="$dir/$NAME"
  if [ "$target" = "$SRC" ]; then say "  $target (already here)"; return; fi
  if [ -e "$target" ] || [ -L "$target" ]; then
    if is_this_skill "$target"; then
      real="$(cd "$target" 2>/dev/null && pwd -P || true)"
      [ -n "$real" ] && [ "$real" = "$SRC" ] && [ "$LINK" = 1 ] && { say "  $target -> $SRC (already linked)"; return; }
      rm -rf "$target"
    else
      say "  skipped $target: a different skill with this name is there" >&2; return
    fi
  fi
  if [ "$LINK" = 1 ]; then
    ln -s "$SRC" "$target"; say "  linked $target -> $SRC"
  else
    mkdir -p "$target"
    tar -C "$SRC" --exclude=./.git --exclude=./dist --exclude='__pycache__' --exclude='*.pyc' \
        --exclude='*.parts' -cf - . | tar -C "$target" -xf -
    say "  copied to $target"
  fi
}

remove_from() {
  local target="$1/$NAME"
  [ -e "$target" ] || [ -L "$target" ] || return 0
  if ! is_this_skill "$target"; then say "  left $target: not this skill"; return; fi
  if [ ! -L "$target" ] && [ "$(cd "$target" && pwd -P)" = "$SRC" ]; then say "  kept $target: this script runs from it"; return; fi
  rm -rf "$target"; say "  removed $target"
}

# ---- Python packages ---------------------------------------------------------------------------
PY=""
find_python() {
  local c
  for c in python3 python; do
    if have "$c" && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      PY="$c"; return 0
    fi
  done
  return 1
}

pip_install() {
  local args=(-m pip install --disable-pip-version-check -r "$SRC/requirements.txt") log status
  [ "$OPTIONAL" = 1 ] && args+=(-r "$SRC/requirements-optional.txt")
  if ! "$PY" -m pip --version >/dev/null 2>&1; then
    "$PY" -m ensurepip --upgrade >/dev/null 2>&1 || "$PY" -m ensurepip --user >/dev/null 2>&1 || {
      say "pip is missing. Install it (Debian/Ubuntu: sudo apt-get install -y python3-pip) and run again." >&2; return 1; }
  fi
  if [ -n "${VIRTUAL_ENV:-}${CONDA_PREFIX:-}" ]; then "$PY" "${args[@]}"; return; fi
  log="$(mktemp)"
  set +e
  "$PY" "${args[@]}" --user 2>&1 | tee "$log"
  status=${PIPESTATUS[0]}
  set -e
  if [ "$status" -ne 0 ] && grep -q -i 'externally.managed' "$log"; then
    say ""
    say "This Python is managed by the system (PEP 668). Installing for your user only with"
    say "--break-system-packages. To keep the packages apart instead, activate a virtualenv and run"
    say "./install.sh --deps-only inside it."
    "$PY" "${args[@]}" --user --break-system-packages && status=0 || status=$?
  elif [ "$status" -ne 0 ] && grep -q -i 'user site-packages are not visible\|Can not perform a .--user. install' "$log"; then
    "$PY" "${args[@]}" && status=0 || status=$?
  fi
  rm -f "$log"
  return "$status"
}

system_install() {
  local sudo=""
  if [ "$(id -u)" -ne 0 ]; then have sudo && sudo="sudo" || { say "  need root or sudo to install system packages" >&2; return 1; }; fi
  # ffmpeg, zbar (QR checks) and, on Linux, the GL libraries skia-python loads
  if have apt-get; then $sudo apt-get update -qq && $sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg libzbar0 libgl1 libegl1
  elif have brew; then brew install ffmpeg zbar
  elif have dnf; then $sudo dnf install -y ffmpeg zbar mesa-libGL mesa-libEGL   # full ffmpeg (libx264) is in RPM Fusion on Fedora
  elif have pacman; then $sudo pacman -S --noconfirm --needed ffmpeg zbar libglvnd
  elif have zypper; then $sudo zypper --non-interactive install ffmpeg zbar Mesa-libGL1 Mesa-libEGL1
  else return 1; fi
}

ffmpeg_hint() {
  say "Install the system packages (ffmpeg with libx264; on Linux also the GL libraries skia-python loads),"
  say "then run tools/check_env.py again:"
  say "  Debian/Ubuntu:  sudo apt-get install -y ffmpeg libzbar0 libgl1 libegl1"
  say "  macOS:          brew install ffmpeg zbar"
  say "  Fedora:         enable RPM Fusion, then sudo dnf install ffmpeg zbar mesa-libGL mesa-libEGL"
  say "  Arch:           sudo pacman -S ffmpeg zbar libglvnd"
  say "  or run:         ./install.sh --deps-only --system-deps"
}

# ---- run ---------------------------------------------------------------------------------------
say "programmatic-motion-video ${VERSION:-}"

if [ "$SKILLS" = 1 ]; then
  DIRS="$(skill_dirs)"
  if [ "$UNINSTALL" = 1 ]; then
    say "Removing the skill:"
    [ -z "$EXTRA_DESTS" ] && [ "$AGENTS" = auto ] && [ -z "$PROJECT" ] && DIRS="$(AGENTS=all skill_dirs)"
    while IFS= read -r d; do [ -n "$d" ] && remove_from "$d"; done <<EOF
$DIRS
EOF
    exit 0
  fi
  say "Installing the skill:"
  while IFS= read -r d; do [ -n "$d" ] && install_to "$d"; done <<EOF
$DIRS
EOF
fi

if [ "$DEPS" = 1 ]; then
  say ""
  if ! find_python; then
    say "Python 3.9 or newer was not found. Install it (python.org, brew install python, apt-get install python3)"
    say "and run: ./install.sh --deps-only"
    exit 1
  fi
  say "Installing Python packages for $("$PY" -c 'import sys; print(sys.executable, sys.version.split()[0])'):"
  pip_install || { say "The Python packages did not install; see the messages above." >&2; exit 1; }

  need_system=0
  have ffmpeg || need_system=1
  "$PY" -c 'import skia' >/dev/null 2>&1 || need_system=1          # usually libGL/libEGL missing on Linux
  if [ "$need_system" = 1 ] || [ "$SYSDEPS" = yes ]; then
    want=0
    [ "$SYSDEPS" = yes ] && want=1
    if [ "$SYSDEPS" = auto ] && [ "$(id -u)" -eq 0 ] && have apt-get; then want=1; fi   # containers
    if [ "$want" = 1 ]; then
      say ""; say "Installing system packages:"
      system_install || { say "  that did not work" >&2; ffmpeg_hint; }
    else
      say ""; ffmpeg_hint
    fi
  fi
  if have ffmpeg; then
    encoders="$(ffmpeg -hide_banner -encoders 2>/dev/null || true)"
    case "$encoders" in
      *" libx264 "*) ;;
      *) say "note: this ffmpeg has no libx264 encoder; install a full build (see tools/check_env.py)" ;;
    esac
  fi

  say ""
  "$PY" "$SRC/tools/check_env.py" --quick || true
fi

if [ "$SKILLS" = 1 ]; then
  say ""
  say "Done. Restart your agent (or start a new session) so it sees the skill, then ask for a video,"
  say "for example: \"Make a 30-second promo video for my app, 1080p, with music.\""
fi
