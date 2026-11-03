#!/bin/bash
# Build the transitional package syslinuxos-system-three (empty, depends on
# syslinuxos-conky-system-three) so that "apt upgrade" migrates existing installs.
set -euo pipefail
PKG_NAME=syslinuxos-system-three
NEW_NAME=syslinuxos-conky-system-three
PKG_VERSION=0.2.0
WORKDIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="${1:-$WORKDIR/dist}"
mkdir -p "$OUTPUT"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
mkdir -p "$STAGING/DEBIAN"
cat > "$STAGING/DEBIAN/control" <<EOT
Package: $PKG_NAME
Version: $PKG_VERSION
Section: oldlibs
Priority: optional
Architecture: all
Depends: $NEW_NAME (>= $PKG_VERSION)
Maintainer: Franco Conidi <fconidi@gmail.com>
Homepage: https://github.com/fconidi/syslinuxos-conky-system-three
Installed-Size: 1
Description: transitional package, syslinuxos-system-three is now syslinuxos-conky-system-three
 This empty package only pulls in syslinuxos-conky-system-three and can be
 safely removed once the upgrade is complete.
EOT
dpkg-deb --root-owner-group --build "$STAGING" "$OUTPUT/${PKG_NAME}_${PKG_VERSION}_all.deb"
