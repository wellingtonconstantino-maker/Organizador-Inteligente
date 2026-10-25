#!/usr/bin/env bash
set -euo pipefail
mkdir -p output
VERSION=0.9.1
PKG="$(mktemp -d)"
trap 'rm -rf "$PKG"' EXIT
mkdir -p "$PKG/DEBIAN" "$PKG/opt/constantino-software" "$PKG/usr/bin" "$PKG/usr/share/applications"
cp -a dist/constantino-organizador/. "$PKG/opt/constantino-software/"
cat > "$PKG/usr/bin/constantino-organizador" <<'EOF'
#!/bin/sh
exec /opt/constantino-software/constantino-organizador "$@"
EOF
chmod +x "$PKG/usr/bin/constantino-organizador"
cat > "$PKG/usr/share/applications/constantino-organizador.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Constantino Software - Organizador Inteligente
Exec=constantino-organizador
Icon=applications-science
Terminal=false
Categories=Utility;Education;
EOF
cat > "$PKG/DEBIAN/control" <<'EOF'
Package: constantino-organizador
Version: 0.9.1
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Constantino Software <nao-informado@invalid.local>
Depends: libc6, libegl1, libopengl0, libxcb-cursor0, libxkbcommon-x11-0
Description: Constantino Software - Organizador Inteligente
 Modulos Geral e Cientifico integrados. Versao experimental.
EOF
chmod 755 "$PKG/DEBIAN" "$PKG/usr/bin" "$PKG/opt" "$PKG/opt/constantino-software"
dpkg-deb --build --root-owner-group "$PKG" "output/Constantino_Software_${VERSION}_amd64.deb"
tar -czf "output/Constantino_Software_${VERSION}_Linux_portatil.tar.gz" -C dist constantino-organizador
