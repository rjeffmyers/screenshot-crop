#!/bin/bash

# Build script for creating .deb package for Screenshot Crop Tool
# Supports Ubuntu 24.04 and Linux Mint 22.1

VERSION="1.0.1"
PACKAGE_NAME="screenshot-crop"
ARCH="all"
MAINTAINER="Screenshot Crop Tool Contributors"
DESCRIPTION="A powerful screenshot tool with monitor selection and cropping"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building ${PACKAGE_NAME} version ${VERSION}${NC}"

# Create build directory structure
BUILD_DIR="build/${PACKAGE_NAME}_${VERSION}_${ARCH}"
rm -rf build
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/48x48/apps"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${BUILD_DIR}/usr/share/doc/${PACKAGE_NAME}"

# Copy the main script
cp screenshot-crop.py "${BUILD_DIR}/usr/bin/screenshot-crop"
chmod 755 "${BUILD_DIR}/usr/bin/screenshot-crop"

# Create control file
cat > "${BUILD_DIR}/DEBIAN/control" << EOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: graphics
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.8), python3-gi, python3-gi-cairo, gir1.2-gtk-3.0, gir1.2-gdk-3.0
Maintainer: ${MAINTAINER}
Description: ${DESCRIPTION}
 Screenshot Crop Tool is a modern screenshot utility for Linux with:
 - Multi-monitor support with visual identification
 - Visual crop interface with drag selection
 - Project folder management with persistent storage
 - Custom file naming for documentation workflows
 - Keyboard shortcuts for efficient operation
Homepage: https://github.com/yourusername/screenshot-crop
EOF

# Create desktop entry
cat > "${BUILD_DIR}/usr/share/applications/screenshot-crop.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Screenshot Crop Tool
Comment=Take screenshots with cropping and monitor selection
Exec=screenshot-crop
Icon=screenshot-crop
Terminal=false
Categories=Graphics;Photography;GTK;
Keywords=screenshot;screen;capture;crop;monitor;
StartupNotify=true
EOF

# Create a simple icon (SVG)
cat > "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps/screenshot-crop.svg" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg width="48" height="48" version="1.1" xmlns="http://www.w3.org/2000/svg">
  <rect x="4" y="8" width="40" height="28" rx="2" fill="#4a90e2" stroke="#2c5aa0" stroke-width="2"/>
  <rect x="8" y="12" width="32" height="20" fill="#ffffff" opacity="0.9"/>
  <rect x="12" y="16" width="24" height="12" fill="none" stroke="#e74c3c" stroke-width="2" stroke-dasharray="4,2"/>
  <circle cx="38" cy="38" r="8" fill="#27ae60"/>
  <path d="M34 38 L36 40 L42 34" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
EOF

# Copy the SVG as 48x48 PNG placeholder (in production, use proper PNG conversion)
cp "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps/screenshot-crop.svg" \
   "${BUILD_DIR}/usr/share/icons/hicolor/48x48/apps/screenshot-crop.svg"

# Copy documentation
cp README.md "${BUILD_DIR}/usr/share/doc/${PACKAGE_NAME}/"
cp LICENSE "${BUILD_DIR}/usr/share/doc/${PACKAGE_NAME}/"

# Create changelog
cat > "${BUILD_DIR}/usr/share/doc/${PACKAGE_NAME}/changelog" << EOF
${PACKAGE_NAME} (${VERSION}) stable; urgency=medium

  * Initial release
  * Multi-monitor support with identification
  * Visual crop interface
  * Project folder management
  * Custom file naming
  * Persistent settings storage

 -- ${MAINTAINER}  $(date -R)
EOF

gzip -9 "${BUILD_DIR}/usr/share/doc/${PACKAGE_NAME}/changelog"

# Create copyright file
cat > "${BUILD_DIR}/usr/share/doc/${PACKAGE_NAME}/copyright" << EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: ${PACKAGE_NAME}
Source: https://github.com/yourusername/screenshot-crop

Files: *
Copyright: 2024 Screenshot Crop Tool Contributors
License: MIT
 $(cat LICENSE | sed 's/^/ /')
EOF

# Set permissions
find "${BUILD_DIR}" -type d -exec chmod 755 {} \;
find "${BUILD_DIR}" -type f -exec chmod 644 {} \;
chmod 755 "${BUILD_DIR}/usr/bin/screenshot-crop"

# Build the package
echo -e "${YELLOW}Building .deb package...${NC}"
dpkg-deb --build "${BUILD_DIR}"

# Move to build directory
mv "build/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb" "build/"

echo -e "${GREEN}✓ Package built successfully: build/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb${NC}"

# Verify the package
echo -e "\n${YELLOW}Package information:${NC}"
dpkg-deb --info "build/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

echo -e "\n${YELLOW}Package contents:${NC}"
dpkg-deb --contents "build/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb" | head -20

echo -e "\n${GREEN}Installation instructions:${NC}"
echo "  sudo dpkg -i build/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo "  sudo apt-get install -f  # If there are dependency issues"

echo -e "\n${GREEN}To uninstall:${NC}"
echo "  sudo apt-get remove ${PACKAGE_NAME}"