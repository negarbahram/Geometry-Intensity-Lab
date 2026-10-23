#!/usr/bin/env bash
# Build a minimal static OpenCV 4.11.0 (core, imgproc, imgcodecs) into cpp/third_party/opencv-install.
# Downloaded from the official GitHub release archive and checked against a pinned SHA-256. libpng, libjpeg and zlib
# come from the copies bundled in the OpenCV source; nothing is installed system-wide.
#
#   cpp/scripts/build_opencv.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="4.11.0"
SHA256="9a7c11f924eff5f8d8070e297b322ee68b9227e003fd600d4b8122198091665f"
THIRD="$ROOT/third_party"
SRC="$THIRD/opencv-$VERSION"
BUILD="$THIRD/opencv-build"
PREFIX="$THIRD/opencv-install"
JOBS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)"

if [ -f "$PREFIX/lib/cmake/opencv4/OpenCVConfig.cmake" ]; then
  echo "OpenCV $VERSION is already built in $PREFIX"
  exit 0
fi
mkdir -p "$THIRD"
ARCHIVE="$THIRD/opencv-$VERSION.tar.gz"
if [ ! -f "$ARCHIVE" ] || ! echo "$SHA256  $ARCHIVE" | shasum -a 256 -c - >/dev/null 2>&1; then
  curl -fSL --retry 3 -o "$ARCHIVE" "https://github.com/opencv/opencv/archive/refs/tags/$VERSION.tar.gz"
  echo "$SHA256  $ARCHIVE" | shasum -a 256 -c - >/dev/null || { echo "checksum mismatch for $ARCHIVE" >&2; exit 1; }
fi
[ -d "$SRC" ] || tar -xzf "$ARCHIVE" -C "$THIRD"

cmake -S "$SRC" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DBUILD_LIST=core,imgproc,imgcodecs \
  -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF -DBUILD_PERF_TESTS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_DOCS=OFF \
  -DBUILD_opencv_apps=OFF -DBUILD_opencv_python3=OFF -DBUILD_JAVA=OFF \
  -DBUILD_ZLIB=ON -DBUILD_JPEG=ON -DBUILD_PNG=ON \
  -DWITH_TIFF=OFF -DWITH_WEBP=OFF -DWITH_OPENJPEG=OFF -DWITH_JASPER=OFF -DWITH_OPENEXR=OFF -DWITH_IMGCODEC_HDR=OFF \
  -DWITH_IMGCODEC_SUNRASTER=OFF -DWITH_IMGCODEC_PXM=OFF -DWITH_IMGCODEC_PFM=OFF -DWITH_GDAL=OFF \
  -DWITH_FFMPEG=OFF -DWITH_GSTREAMER=OFF -DWITH_AVFOUNDATION=OFF -DWITH_OPENCL=OFF -DWITH_IPP=OFF -DWITH_ITT=OFF \
  -DWITH_ADE=OFF -DWITH_PROTOBUF=OFF -DWITH_QUIRC=OFF -DWITH_EIGEN=OFF -DWITH_LAPACK=OFF -DOPENCV_GENERATE_PKGCONFIG=OFF
cmake --build "$BUILD" --parallel "$JOBS"
cmake --install "$BUILD"
echo "OpenCV $VERSION installed in $PREFIX"
