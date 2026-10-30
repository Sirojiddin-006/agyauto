#!/bin/sh
# agyauto installer:  curl -fsSL https://raw.githubusercontent.com/Sirojiddin-006/agyauto/main/install.sh | sh
# Env: AGYAUTO_REF (branch/tag, default main), AGYAUTO_TARBALL (override download URL, for testing)
set -eu

REPO="Sirojiddin-006/agyauto"
REF="${AGYAUTO_REF:-main}"
URL="${AGYAUTO_TARBALL:-https://github.com/$REPO/archive/refs/heads/$REF.tar.gz}"
case "$REF" in v[0-9]*) [ -n "${AGYAUTO_TARBALL:-}" ] || URL="https://github.com/$REPO/archive/refs/tags/$REF.tar.gz" ;; esac

say() { printf '%s\n' "$*"; }
die() { printf 'agyauto install: %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 not found (need 3.8+). Install it first: apt install python3 / brew install python3"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || die "python3 >= 3.8 required"
python3 -c 'import curses, pty, sqlite3' 2>/dev/null || die "python3 is missing curses/pty/sqlite3 modules (Debian/Ubuntu: apt install python3-full)"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT INT TERM

say "==> downloading agyauto ($REF)"
if command -v curl >/dev/null 2>&1; then curl -fsSL "$URL" -o "$TMP/src.tgz"
elif command -v wget >/dev/null 2>&1; then wget -qO "$TMP/src.tgz" "$URL"
else die "need curl or wget"; fi

mkdir "$TMP/x"
tar -xzf "$TMP/src.tgz" -C "$TMP/x"
SRC="$(find "$TMP/x" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[ -f "$SRC/VERSION" ] && [ -f "$SRC/bin/agyauto" ] || die "unexpected archive layout"

say "==> installing"
python3 "$SRC/bin/agyauto" _install "$SRC"

BIN="$HOME/.local/bin"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *)
    case "$(basename "${SHELL:-sh}")" in
      zsh)  RC="$HOME/.zshrc"; LINE='export PATH="$HOME/.local/bin:$PATH"' ;;
      fish) RC="$HOME/.config/fish/config.fish"; LINE='fish_add_path $HOME/.local/bin' ;;
      bash) if [ "$(uname)" = Darwin ]; then RC="$HOME/.bash_profile"; else RC="$HOME/.bashrc"; fi
            LINE='export PATH="$HOME/.local/bin:$PATH"' ;;
      *)    RC="$HOME/.profile"; LINE='export PATH="$HOME/.local/bin:$PATH"' ;;
    esac
    mkdir -p "$(dirname "$RC")"
    if ! grep -qs 'agyauto PATH' "$RC" 2>/dev/null; then
      printf '\n# agyauto PATH\n%s\n' "$LINE" >> "$RC"
      say "==> added ~/.local/bin to PATH in $RC (open a new terminal or: source $RC)"
    fi
    ;;
esac

"$BIN/agyauto" doctor || true
say ""
say "agyauto $("$BIN/agyauto" version) installed."
say "  agyauto                    open the dashboard"
say "  agyauto agy                run agy with auto-approval"
say "  agyauto ssh user@host      run ssh, then start agy on the server"
say "  agyauto update | uninstall"
