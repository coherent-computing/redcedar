#!/bin/bash
# Build and publish redcedar to PyPI
# Usage: ./build_pypi.sh            (build only)
#        ./build_pypi.sh testpypi   (build and upload to TestPyPI)
#        ./build_pypi.sh upload     (build and upload to PyPI)
#
# Can run from anywhere — auto-navigates to repo root.

# Navigate to repo root (one level up from dev/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "=== Building redcedar package ==="

# Clean previous builds
rm -rf dist/ build/ redcedar.egg-info/

# Build
python -m build --no-isolation || { echo ""; echo "=== Build FAILED ==="; exit 1; }

echo ""
echo "=== Build complete ==="
ls -l dist/

if [ "$1" = "upload" ]; then
    echo ""
    echo "=== Uploading to PyPI ==="
    twine upload dist/*
elif [ "$1" = "testpypi" ]; then
    echo ""
    echo "=== Uploading to TestPyPI ==="
    twine upload --repository testpypi dist/*
else
    echo ""
    echo "To upload: ./build_pypi.sh testpypi   (TestPyPI first)"
    echo "           ./build_pypi.sh upload     (PyPI)"
fi
