#!/bin/bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd)
SUITE=trixie
MIRROR=${MANIFESTOS_MIRROR:-http://deb.debian.org/debian}
VERSION=${MANIFESTOS_VERSION:-$(date -u +%Y.%m.%d)}
HOME_URL=${MANIFESTOS_HOME_URL:-https://github.com/manifest-linux/manifestos}
WORK=${MANIFESTOS_WORK_DIR:-/var/tmp/manifestos-build}
OUT=${MANIFESTOS_OUT_DIR:-$ROOT/out}
CHROOT=$WORK/chroot
ISO=$WORK/iso
DEBS=$WORK/debs
POOL=$WORK/pool
ISO_NAME=manifestos-$VERSION-amd64.iso
MOUNTS=(dev dev/pts proc sys)

export DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8

step() {
	printf '\n==> %s\n' "$*"
}

in_chroot() {
	chroot "$CHROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8 "$@"
}

unmount_chroot() {
	for ((i = ${#MOUNTS[@]} - 1; i >= 0; i--)); do
		if mountpoint -q "$CHROOT/${MOUNTS[i]}"; then
			umount -l "$CHROOT/${MOUNTS[i]}"
		fi
	done
}

newest() {
	find "$CHROOT/boot" -maxdepth 1 -name "$1" | sort -V | tail -n 1
}

if [ "$(id -u)" -ne 0 ]; then
	echo "mkiso.sh must run as root" >&2
	exit 1
fi
if [ "$(dpkg --print-architecture)" != amd64 ]; then
	echo "mkiso.sh must run on an amd64 Debian system" >&2
	exit 1
fi

step "Installing build tools"
apt-get update
apt-get install -y --no-install-recommends \
	apt-utils ca-certificates debootstrap dosfstools dpkg-dev fontconfig fonts-comfortaa \
	grub-common grub-efi-amd64-bin grub-pc-bin kde-style-breeze-data librsvg2-bin mtools \
	python3 squashfs-tools xorriso

trap unmount_chroot EXIT
unmount_chroot
rm -rf "$WORK"
mkdir -p "$WORK" "$OUT" "$ISO/live" "$ISO/.disk" "$POOL"

step "Building ManifestOS packages $VERSION"
"$ROOT/packages/build-debs.sh" "$DEBS" "$VERSION" "$HOME_URL"

step "Bootstrapping Debian $SUITE"
debootstrap --variant=minbase --arch=amd64 "$SUITE" "$CHROOT" "$MIRROR"
rm -f "$CHROOT/etc/apt/sources.list"
install -m 644 "$ROOT/config/debian.sources" "$CHROOT/etc/apt/sources.list.d/debian.sources"
cp /etc/resolv.conf "$CHROOT/etc/resolv.conf"
printf '#!/bin/sh\nexit 101\n' > "$CHROOT/usr/sbin/policy-rc.d"
chmod 755 "$CHROOT/usr/sbin/policy-rc.d"
echo manifestos > "$CHROOT/etc/hostname"
for mount in "${MOUNTS[@]}"; do
	mount --bind "/$mount" "$CHROOT/$mount"
done

step "Installing the desktop"
mapfile -t PACKAGES < <(grep -Ev '^[[:space:]]*(#|$)' "$ROOT/config/packages.txt")
in_chroot apt-get update
in_chroot apt-get -y full-upgrade
in_chroot apt-get install -y --no-install-recommends "${PACKAGES[@]}"

step "Installing ManifestOS packages"
mkdir -p "$CHROOT/tmp/manifestos-debs"
cp "$DEBS"/*.deb "$CHROOT/tmp/manifestos-debs/"
in_chroot sh -c 'apt-get install -y --no-install-recommends /tmp/manifestos-debs/*.deb'
rm -rf "$CHROOT/tmp/manifestos-debs"

step "Customizing the system"
install -m 755 "$ROOT/config/customize-chroot.sh" "$CHROOT/tmp/customize-chroot.sh"
in_chroot /tmp/customize-chroot.sh
rm "$CHROOT/tmp/customize-chroot.sh"

step "Collecting bootloader packages for offline installs"
for set in "grub-efi grub-efi-amd64" "grub-pc" "cryptsetup-initramfs cryptsetup keyutils"; do
	in_chroot apt-get clean
	read -r -a wanted <<< "$set"
	in_chroot apt-get install -y --download-only --no-install-recommends "${wanted[@]}"
	find "$CHROOT/var/cache/apt/archives" -maxdepth 1 -name '*.deb' -exec cp {} "$POOL/" \;
done
mkdir -p "$ISO/pool/main" "$ISO/dists/$SUITE/main/binary-amd64"
cp "$POOL"/*.deb "$ISO/pool/main/"
(cd "$ISO" && apt-ftparchive packages pool/main > "dists/$SUITE/main/binary-amd64/Packages")
gzip -9kn "$ISO/dists/$SUITE/main/binary-amd64/Packages"
apt-ftparchive \
	-o APT::FTPArchive::Release::Origin=ManifestOS \
	-o APT::FTPArchive::Release::Suite="$SUITE" \
	-o APT::FTPArchive::Release::Codename="$SUITE" \
	-o APT::FTPArchive::Release::Components=main \
	-o APT::FTPArchive::Release::Architectures=amd64 \
	release "$ISO/dists/$SUITE" > "$WORK/Release"
mv "$WORK/Release" "$ISO/dists/$SUITE/Release"

step "Cleaning up"
in_chroot apt-get clean
in_chroot update-initramfs -u -k all
unmount_chroot
rm -rf "$CHROOT"/var/lib/apt/lists/* "$CHROOT"/tmp/* "$CHROOT"/var/tmp/* "$CHROOT/root/.bash_history"
find "$CHROOT/var/log" -type f -delete
: > "$CHROOT/etc/machine-id"
rm -f "$CHROOT/usr/sbin/policy-rc.d" "$CHROOT/etc/resolv.conf"

step "Assembling the ISO"
cp "$(newest 'vmlinuz-*')" "$ISO/live/vmlinuz"
cp "$(newest 'initrd.img-*')" "$ISO/live/initrd.img"
mksquashfs "$CHROOT" "$ISO/live/filesystem.squashfs" -noappend -comp xz -Xbcj x86 -b 1M
mkdir -p "$ISO/boot/grub/themes"
cp -a "$CHROOT/usr/share/grub/themes/manifestos" "$ISO/boot/grub/themes/"
install -m 644 "$ROOT/config/grub.cfg" "$ISO/boot/grub/grub.cfg"
echo "ManifestOS $VERSION amd64" > "$ISO/.disk/info"
rm -f "$OUT/$ISO_NAME"
grub-mkrescue -o "$OUT/$ISO_NAME" "$ISO" -- -volid MANIFESTOS
(cd "$OUT" && sha256sum "$ISO_NAME" > "$ISO_NAME.sha256")

step "Done"
ls -lh "$OUT/$ISO_NAME"
