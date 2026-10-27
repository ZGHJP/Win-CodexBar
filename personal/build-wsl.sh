#!/usr/bin/env bash
# Invoke after building the frontend on Windows. The supplied environment file
# configures the existing cargo-xwin installation; no tool installation occurs.
set -euo pipefail
if [[ $# != 1 ]]; then
  echo 'Usage: bash personal/build-wsl.sh /absolute/path/to/existing-build-env.sh' >&2
  exit 2
fi
source "$1"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export BUILD_NUMBER=personal-0.70.0-jp.1
cd "$root/apps/desktop-tauri"
cargo tauri build --runner cargo-xwin --target x86_64-pc-windows-msvc --no-bundle --config '{"build":{"beforeBuildCommand":""}}'
cd "$root"
cargo xwin build -p codexbar --bin codexbar --release --target x86_64-pc-windows-msvc
