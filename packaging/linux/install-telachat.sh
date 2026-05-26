#!/usr/bin/env sh
set -eu

TELACHAT_VERSION="0.54.1"
DEFAULT_RELEASE_URL="https://github.com/H234598/telachat/releases/download/v${TELACHAT_VERSION}/telachat.pyz"

usage() {
    cat <<'USAGE'
Usage: install-telachat.sh [options]

Install Telachat from a local or release zipapp into a user or system prefix.

Options:
  --prefix DIR              Install prefix. Default: $HOME/.local
  --python PATH             Python executable. Default: python3
  --zipapp PATH_OR_URL      Use this telachat.pyz instead of auto-detecting.
  --desktop-dir DIR         Desktop shortcut directory. Auto-detected by default.
  --no-desktop-shortcut     Do not create a desktop shortcut copy.
  --no-menu-entry           Do not install the application menu .desktop file.
  -h, --help                Show this help.
USAGE
}

die() {
    printf 'install-telachat: %s\n' "$*" >&2
    exit 1
}

say() {
    printf '%s\n' "$*"
}

prefix="${PREFIX:-$HOME/.local}"
python="${PYTHON:-python3}"
zipapp_source="${TELACHAT_ZIPAPP_SOURCE:-}"
desktop_dir=""
install_desktop_shortcut=1
install_menu_entry=1

while [ "$#" -gt 0 ]; do
    case "$1" in
        --prefix)
            [ "$#" -ge 2 ] || die "--prefix needs a directory"
            prefix=$2
            shift 2
            ;;
        --python)
            [ "$#" -ge 2 ] || die "--python needs an executable"
            python=$2
            shift 2
            ;;
        --zipapp)
            [ "$#" -ge 2 ] || die "--zipapp needs a path or URL"
            zipapp_source=$2
            shift 2
            ;;
        --desktop-dir)
            [ "$#" -ge 2 ] || die "--desktop-dir needs a directory"
            desktop_dir=$2
            shift 2
            ;;
        --no-desktop-shortcut)
            install_desktop_shortcut=0
            shift
            ;;
        --no-menu-entry)
            install_menu_entry=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown option: $1"
            ;;
    esac
done

command -v "$python" >/dev/null 2>&1 || die "Python executable not found: $python"
"$python" - <<'PY' || die "Python 3.11 or newer is required"
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/../.." 2>/dev/null && pwd || printf '%s' "$script_dir")

if [ -z "$zipapp_source" ]; then
    if [ -f "$repo_root/dist/telachat.pyz" ]; then
        zipapp_source="$repo_root/dist/telachat.pyz"
    else
        zipapp_source="$DEFAULT_RELEASE_URL"
    fi
fi

prefix=${prefix%/}
app_dir="$prefix/lib/telachat"
bin_dir="$prefix/bin"
man_dir="$prefix/share/man/man1"
apps_dir="$prefix/share/applications"
icon_dir="$prefix/share/icons/hicolor/256x256/apps"
tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/telachat-install.XXXXXX")
trap 'rm -rf "$tmp_dir"' EXIT INT HUP TERM

copy_or_download() {
    source=$1
    dest=$2
    case "$source" in
        http://*|https://*)
            if command -v curl >/dev/null 2>&1; then
                curl -fsSL "$source" -o "$dest"
            elif command -v wget >/dev/null 2>&1; then
                wget -qO "$dest" "$source"
            else
                "$python" - "$source" "$dest" <<'PY'
from __future__ import annotations

import sys
import urllib.request

urllib.request.urlretrieve(sys.argv[1], sys.argv[2])
PY
            fi
            ;;
        *)
            [ -f "$source" ] || die "zipapp not found: $source"
            cp "$source" "$dest"
            ;;
    esac
}

render_wrapper() {
    name=$1
    dest=$2
    pyz=$3
    template="$repo_root/packaging/linux/wrappers/${name}.in"
    if [ -f "$template" ]; then
        sed "s|@TELACHAT_PYZ@|$pyz|g" "$template" > "$dest"
    else
        case "$name" in
            telachat)
                cat > "$dest" <<EOF
#!/usr/bin/env sh
set -eu
TELACHAT_PYZ="\${TELACHAT_PYZ:-$pyz}"
TELACHAT_PYTHON="\${TELACHAT_PYTHON:-python3}"
exec "\$TELACHAT_PYTHON" "\$TELACHAT_PYZ" "\$@"
EOF
                ;;
            telachat-tk)
                cat > "$dest" <<EOF
#!/usr/bin/env sh
set -eu
TELACHAT_PYZ="\${TELACHAT_PYZ:-$pyz}"
TELACHAT_PYTHON="\${TELACHAT_PYTHON:-python3}"
PYTHONPATH="\$TELACHAT_PYZ\${PYTHONPATH:+:\$PYTHONPATH}"
export PYTHONPATH
exec "\$TELACHAT_PYTHON" -m telachat.tkgui "\$@"
EOF
                ;;
            telachat-gtk)
                cat > "$dest" <<EOF
#!/usr/bin/env sh
set -eu
TELACHAT_PYZ="\${TELACHAT_PYZ:-$pyz}"
TELACHAT_PYTHON="\${TELACHAT_PYTHON:-python3}"
PYTHONPATH="\$TELACHAT_PYZ\${PYTHONPATH:+:\$PYTHONPATH}"
export PYTHONPATH
exec "\$TELACHAT_PYTHON" -m telachat.gtkgui "\$@"
EOF
                ;;
            telachat-gui)
                cat > "$dest" <<EOF
#!/usr/bin/env sh
set -eu
TELACHAT_PYZ="\${TELACHAT_PYZ:-$pyz}"
TELACHAT_PYTHON="\${TELACHAT_PYTHON:-python3}"
PYTHONPATH="\$TELACHAT_PYZ\${PYTHONPATH:+:\$PYTHONPATH}"
export PYTHONPATH
if "\$TELACHAT_PYTHON" - <<'PY' >/dev/null 2>&1; then
import gi
gi.require_version("Gtk", "4.0")
PY
    exec "\$TELACHAT_PYTHON" -m telachat.gtkgui "\$@"
fi
exec "\$TELACHAT_PYTHON" -m telachat.tkgui "\$@"
EOF
                ;;
            *)
                die "unknown wrapper: $name"
                ;;
        esac
    fi
    chmod 0755 "$dest"
}

choose_desktop_dir() {
    if [ -n "$desktop_dir" ]; then
        printf '%s\n' "$desktop_dir"
        return
    fi
    user_dirs="${XDG_CONFIG_HOME:-$HOME/.config}/user-dirs.dirs"
    if [ -f "$user_dirs" ]; then
        value=$(sed -n 's/^XDG_DESKTOP_DIR="\([^"]*\)".*/\1/p' "$user_dirs" | head -n 1)
        if [ -n "$value" ]; then
            value=$(printf '%s' "$value" | sed "s|^\$HOME|$HOME|")
            printf '%s\n' "$value"
            return
        fi
    fi
    if [ -d "$HOME/Schreibtisch" ]; then
        printf '%s\n' "$HOME/Schreibtisch"
    else
        printf '%s\n' "$HOME/Desktop"
    fi
}

choose_gui_exec() {
    gtk_ok=0
    tk_ok=0
    "$python" - <<'PY' >/dev/null 2>&1 && gtk_ok=1 || gtk_ok=0
import gi
gi.require_version("Gtk", "4.0")
PY
    "$python" - <<'PY' >/dev/null 2>&1 && tk_ok=1 || tk_ok=0
import tkinter
PY
    if [ "$gtk_ok" -eq 1 ]; then
        printf '%s\n' "$bin_dir/telachat-gtk"
    elif [ "$tk_ok" -eq 1 ]; then
        printf '%s\n' "$bin_dir/telachat-tk"
    else
        printf '%s\n' "$bin_dir/telachat"
    fi
}

install_desktop_file() {
    dest=$1
    exec_path=$2
    template="$repo_root/packaging/linux/telachat.desktop.in"
    if [ -f "$template" ]; then
        sed "s|@TELACHAT_EXEC@|$exec_path|g" "$template" > "$dest"
    else
        cat > "$dest" <<EOF
[Desktop Entry]
Type=Application
Version=1.5
Name=Telachat
Comment=Local configurable AI chat client
Exec=$exec_path
Icon=telachat
Terminal=false
Categories=Network;Chat;Utility;
StartupNotify=true
EOF
    fi
    chmod 0755 "$dest"
}

install_icon() {
    dest=$1
    icon="$repo_root/src/telachat/assets/icons-png/06_round_orange_cat_icon.png"
    if [ -f "$icon" ]; then
        cp "$icon" "$dest"
    else
        "$python" - "$dest" <<'PY'
from __future__ import annotations

import base64
import sys

png = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/x8AAwMB/6X4n0sAAAAASUVORK5CYII="
)
open(sys.argv[1], "wb").write(base64.b64decode(png))
PY
    fi
    chmod 0644 "$dest"
}

mkdir -p "$app_dir" "$bin_dir" "$man_dir" "$icon_dir"
if [ "$install_menu_entry" -eq 1 ]; then
    mkdir -p "$apps_dir"
fi

copy_or_download "$zipapp_source" "$tmp_dir/telachat.pyz"
"$python" "$tmp_dir/telachat.pyz" --version >/dev/null || die "zipapp smoke check failed"
install -m 0755 "$tmp_dir/telachat.pyz" "$app_dir/telachat.pyz"

for wrapper in telachat telachat-tk telachat-gtk telachat-gui; do
    render_wrapper "$wrapper" "$bin_dir/$wrapper" "$app_dir/telachat.pyz"
done

for manpage in telachat.1 telachat-tk.1 telachat-gtk.1; do
    if [ -f "$repo_root/docs/man/$manpage" ]; then
        install -m 0644 "$repo_root/docs/man/$manpage" "$man_dir/$manpage"
    fi
done

install_icon "$icon_dir/telachat.png"
gui_exec=$(choose_gui_exec)

if [ "$install_menu_entry" -eq 1 ]; then
    install_desktop_file "$apps_dir/telachat.desktop" "$gui_exec"
fi

if [ "$install_desktop_shortcut" -eq 1 ]; then
    target_desktop_dir=$(choose_desktop_dir)
    mkdir -p "$target_desktop_dir"
    install_desktop_file "$target_desktop_dir/Telachat.desktop" "$gui_exec"
fi

if command -v update-desktop-database >/dev/null 2>&1 && [ "$install_menu_entry" -eq 1 ]; then
    update-desktop-database "$apps_dir" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q "$prefix/share/icons/hicolor" >/dev/null 2>&1 || true
fi

say "Installed Telachat $TELACHAT_VERSION"
say "  Prefix: $prefix"
say "  CLI:    $bin_dir/telachat"
say "  GUI:    $gui_exec"
if [ "$install_desktop_shortcut" -eq 1 ]; then
    say "  Desktop shortcut: $(choose_desktop_dir)/Telachat.desktop"
fi
