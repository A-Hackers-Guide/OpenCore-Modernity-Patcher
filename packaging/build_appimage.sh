#!/usr/bin/env bash
# build_appimage.sh: wrap the PyInstaller one-folder build into an AppImage
#
# Usage: packaging/build_appimage.sh <output-file.AppImage>
# Needs: dist/OpenCore-Modernity-Patcher/ (from pyinstaller) and packaging/build/icon.png
set -euo pipefail

OUT="${1:?usage: build_appimage.sh <output.AppImage>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPDIR="$ROOT/packaging/build/AppDir"
NAME="OpenCore-Modernity-Patcher"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"

cp -a "$ROOT/dist/$NAME/." "$APPDIR/usr/bin/"
cp "$ROOT/packaging/build/icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/$NAME.png"
cp "$ROOT/packaging/build/icon.png" "$APPDIR/$NAME.png"

cat > "$APPDIR/$NAME.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=OpenCore Modernity Patcher
Comment=Build OpenCore for PCs and KVM virtual machines
Exec=$NAME
Icon=$NAME
Categories=System;Utility;
Terminal=false
EOF
cp "$APPDIR/$NAME.desktop" "$APPDIR/usr/share/applications/"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/OpenCore-Modernity-Patcher" "$@"
EOF
chmod +x "$APPDIR/AppRun"

TOOL="$ROOT/packaging/build/appimagetool"
if [ ! -x "$TOOL" ]; then
  curl -fsSL -o "$TOOL" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi

# CI runners have no FUSE; extract-and-run avoids needing it
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" --no-appstream "$APPDIR" "$OUT"
echo "Built $OUT"
