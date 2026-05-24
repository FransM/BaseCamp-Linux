#!/usr/bin/env bash
# Build the Debian-compatible AppImage in a container (glibc 2.36).
#
# Produces BaseCamp-Linux-x86_64-debian.AppImage at the repo root. The Fedora
# build is made natively (see the .spec files + appimagetool); this one needs a
# Debian environment for the older glibc, hence the container.
set -euo pipefail
cd "$(dirname "$0")"

IMAGE=basecamp-debian-builder
OWNER_UID=$(stat -c %u .)
OWNER_GID=$(stat -c %g .)

echo ">> Building builder image ($IMAGE)…"
docker build -f Dockerfile.debian -t "$IMAGE" .

echo ">> Building binaries + AppImage inside the container…"
docker run --rm -v "$PWD":/work -w /work "$IMAGE" bash -euc '
    rm -rf build_debian dist_debian AppDir_debian
    for spec in BaseCamp-Linux basecamp-controller basecamp-tray \
                everest60-controller makalu-controller; do
        echo "--- pyinstaller ${spec}.spec ---"
        pyinstaller --noconfirm --clean \
            --distpath dist_debian --workpath build_debian "${spec}.spec"
    done

    mkdir -p AppDir_debian/usr/bin
    cp -a dist_debian/BaseCamp-Linux/. AppDir_debian/usr/bin/
    cp -a dist_debian/basecamp-controller dist_debian/basecamp-tray \
          dist_debian/everest60-controller dist_debian/makalu-controller \
          AppDir_debian/usr/bin/
    cp AppDir/AppRun AppDir/basecamp-linux.desktop AppDir/basecamp-linux.png AppDir_debian/
    chmod +x AppDir_debian/AppRun AppDir_debian/usr/bin/BaseCamp-Linux \
             AppDir_debian/usr/bin/basecamp-controller \
             AppDir_debian/usr/bin/basecamp-tray \
             AppDir_debian/usr/bin/everest60-controller \
             AppDir_debian/usr/bin/makalu-controller

    ARCH=x86_64 appimagetool --no-appstream AppDir_debian \
        BaseCamp-Linux-x86_64-debian.AppImage

    chown '"$OWNER_UID:$OWNER_GID"' BaseCamp-Linux-x86_64-debian.AppImage
    rm -rf build_debian dist_debian AppDir_debian
'
echo ">> Done: BaseCamp-Linux-x86_64-debian.AppImage"
