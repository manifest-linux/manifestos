#!/bin/bash
set -euo pipefail

sed -i -E 's/^# *(en_US\.UTF-8 UTF-8)/\1/; s/^# *(tr_TR\.UTF-8 UTF-8)/\1/' /etc/locale.gen
locale-gen
update-locale LANG=en_US.UTF-8

sed -i 's/^branding: .*/branding: manifestos/' /etc/calamares/settings.conf
sed -i -E \
	-e '/^(Name|GenericName|Comment)\[/d' \
	-e 's/^Name=.*/Name=Install ManifestOS/' \
	-e 's/^Icon=.*/Icon=manifestos/' \
	/usr/share/applications/calamares-install-debian.desktop

flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

cat >> /etc/skel/.bashrc <<'EOF'

if [ -z "${MANIFESTOS_QUIET:-}" ] && command -v manifest >/dev/null; then
	manifest banner
fi
EOF

plymouth-set-default-theme manifestos
systemctl set-default graphical.target
