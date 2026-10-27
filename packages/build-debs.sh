#!/bin/bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:?usage: build-debs.sh OUT_DIR VERSION HOME_URL}
VERSION=${2:?usage: build-debs.sh OUT_DIR VERSION HOME_URL}
HOME_URL=${3:?usage: build-debs.sh OUT_DIR VERSION HOME_URL}
PACKAGES=(manifestos-apps manifestos-artwork manifestos-base)

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$OUT"
for package in "${PACKAGES[@]}"; do
	cp -a "$ROOT/packages/$package" "$STAGE/$package"
done

install -d "$STAGE/manifestos-apps/usr/share/manifestos/i18n"
install -m 644 "$ROOT/data/members.json" "$ROOT/data/events.json" "$STAGE/manifestos-apps/usr/share/manifestos/"
install -m 644 "$ROOT"/data/i18n/*.json "$STAGE/manifestos-apps/usr/share/manifestos/i18n/"
python3 "$ROOT/art/make_art.py" "$STAGE/manifestos-artwork"

for package in "${PACKAGES[@]}"; do
	dir=$STAGE/$package
	find "$dir" \( -name '.DS_Store' -o -name '__pycache__' \) -prune -exec rm -rf {} +
	grep -rlI -e '@VERSION@' -e '@HOME_URL@' "$dir" | while read -r file; do
		sed -i -e "s|@VERSION@|$VERSION|g" -e "s|@HOME_URL@|$HOME_URL|g" "$file"
	done
	find "$dir" -type d -exec chmod 755 {} +
	find "$dir" -type f -exec chmod 644 {} +
	find "$dir/DEBIAN" -type f \( -name preinst -o -name postinst -o -name prerm -o -name postrm \) -exec chmod 755 {} +
	for exec_dir in usr/bin usr/lib/live/config; do
		if [ -d "$dir/$exec_dir" ]; then
			find "$dir/$exec_dir" -type f -exec chmod 755 {} +
		fi
	done
	if [ -d "$dir/etc" ]; then
		(cd "$dir" && find etc -type f | sed 's|^|/|' | LC_ALL=C sort) > "$dir/DEBIAN/conffiles"
	fi
	size=$(du -sk --exclude=DEBIAN "$dir" | cut -f1)
	sed -i "/^Version:/a Installed-Size: $size" "$dir/DEBIAN/control"
	dpkg-deb --root-owner-group -Zxz --build "$dir" "$OUT/${package}_${VERSION}_all.deb"
done
