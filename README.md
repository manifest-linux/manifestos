# ManifestOS

ManifestOS is an unofficial, fan-made Linux distribution for fans of the Turkish girl group manifest. It is Debian 13 (trixie) with a pastel KDE Plasma desktop, a bias picker that themes the whole desktop after your favorite member, Manifest Hub, birthday reminders and a countdown widget.

It is not affiliated with manifest or Hypers New Media. No music, official photos or logos are shipped; all artwork is generated from `art/make_art.py`.

## Download

Every push to `main` builds an ISO with GitHub Actions and publishes it on the Releases page. Write it to a USB stick (balenaEtcher, Rufus in DD mode or Ventoy) and boot with Secure Boot turned off.

## Build locally

You need Docker. On Apple Silicon the build runs under amd64 emulation and takes noticeably longer.

```bash
./build.sh
```

The ISO and its checksum land in `out/`. `MANIFESTOS_VERSION`, `MANIFESTOS_HOME_URL` and `MANIFESTOS_MIRROR` are passed through to the build if set.

Unit tests for the shared Python code:

```bash
python3 -m unittest discover -s tests -v
```

## How it fits together

- `mkiso.sh` runs inside a Debian container: it bootstraps trixie, installs `config/packages.txt`, installs the three ManifestOS packages, runs `config/customize-chroot.sh` and builds a hybrid BIOS/UEFI ISO with `grub-mkrescue`.
- `packages/` holds the source trees of `manifestos-base` (os-release diversion, GRUB defaults, live session tweak), `manifestos-artwork` (themes, splash, installer branding) and `manifestos-apps` (Manifest Hub, bias picker, `manifest` command, reminders, Plasma widget). `packages/build-debs.sh` turns them into `.deb` files.
- `data/members.json` is the single source for member names, birthdays, colors and the discography. Member colors are ManifestOS picks, not official colors. `data/i18n/tr.json` holds the Turkish strings.
- Calamares (Debian settings) installs the system. Its bootloader step installs `grub-efi` or `grub-pc` with apt, so the ISO carries a small apt repository under `pool/` and `dists/` with those packages to make offline installs work.
- `docs/` is the GitHub Pages site (Settings, Pages, deploy from `main` and `/docs`).
