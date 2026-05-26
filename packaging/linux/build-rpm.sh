#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT"

command -v rpmbuild >/dev/null 2>&1 || {
    printf 'rpmbuild is required. Install rpm-build on RPM-based systems.\n' >&2
    exit 1
}

VERSION=$(python3 - <<'PY'
from pathlib import Path
import tomllib

data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
print(data["project"]["version"])
PY
)

TOPDIR="$ROOT/dist/rpm"
NAME="telachat"
mkdir -p "$TOPDIR"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

tar \
    --exclude-vcs \
    --exclude='./dist' \
    --exclude='*/__pycache__' \
    --exclude='*.pyc' \
    --transform "s|^\\.|$NAME-$VERSION|" \
    -czf "$TOPDIR/SOURCES/$NAME-$VERSION.tar.gz" \
    .

rpmbuild \
    --define "_topdir $TOPDIR" \
    --define "_version $VERSION" \
    -ba packaging/rpm/telachat.spec

find "$TOPDIR/RPMS" "$TOPDIR/SRPMS" -type f \
    \( -name '*.rpm' -o -name '*.src.rpm' \) -print | sort
