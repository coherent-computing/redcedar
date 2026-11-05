@echo off
REM Build and publish redcedar to PyPI
REM Usage: build_pypi.bat            (build only)
REM        build_pypi.bat testpypi   (build and upload to TestPyPI)
REM        build_pypi.bat upload     (build and upload to PyPI)
REM
REM Can run from anywhere — auto-navigates to repo root.

REM Navigate to repo root (one level up from dev\)
pushd "%~dp0.."

echo === Building redcedar package ===

REM Clean previous builds
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist redcedar.egg-info rmdir /s /q redcedar.egg-info

REM Build
python -m build --no-isolation
set BUILD_RC=%errorlevel%

if %BUILD_RC% neq 0 (
    echo.
    echo === Build FAILED ===
    popd
    exit /b %BUILD_RC%
)

echo.
echo === Build complete ===
dir dist\

if "%1"=="upload" (
    echo.
    echo === Uploading to PyPI ===
    twine upload dist/*
) else if "%1"=="testpypi" (
    echo.
    echo === Uploading to TestPyPI ===
    twine upload --repository testpypi dist/*
) else (
    echo.
    echo To upload: build_pypi.bat testpypi   ^(TestPyPI first^)
    echo            build_pypi.bat upload     ^(PyPI^)
)

popd
