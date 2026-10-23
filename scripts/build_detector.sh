#!/usr/bin/env bash
# Build the existing AIxAM detector CLI (services/geometry-detect) from a pinned commit, outside the AIxAM checkout.
# Read-only use of the AIxAM repository: `git archive` exports the source, and its already-built OpenCV 4.11 install
# and cpp-httplib header are used in place. Nothing in the repository is written.
#
#   scripts/build_detector.sh [AIXAM_WORKTREE] [COMMIT]
set -euo pipefail
LAB="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${1:-/Users/apple/Downloads/AIxAM/.claude/worktrees/geometry-integration}"
COMMIT="${2:-4ca9cf58e9cc73f3c8bde9b64aab69b38c9f077c}"
SVC="$REPO/services/geometry-detect"
SRC="$LAB/third_party/geometry-detect-src"
BUILD="$LAB/third_party/geometry-detect-build"

OPENCV_DIR="$SVC/third_party/opencv-install/lib/cmake/opencv4"
[ -f "$OPENCV_DIR/OpenCVConfig.cmake" ] || { echo "OpenCV 4.11 install not found at $OPENCV_DIR (run the service's scripts/build.sh once)"; exit 1; }

rm -rf "$SRC" && mkdir -p "$SRC"
git -C "$REPO" archive "$COMMIT" services/geometry-detect | tar -x -C "$SRC"
S="$SRC/services/geometry-detect"
mkdir -p "$S/third_party/httplib-0.18.7"
cp "$SVC/third_party/httplib-0.18.7/httplib.h" "$S/third_party/httplib-0.18.7/"
cmake -S "$S" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release -DOpenCV_DIR="$OPENCV_DIR" > "$LAB/third_party/build.log"
cmake --build "$BUILD" --target geometry-detect-cli -j 8 >> "$LAB/third_party/build.log"
echo "$COMMIT" > "$BUILD/COMMIT"
echo "built $BUILD/geometry-detect-cli from $COMMIT"
