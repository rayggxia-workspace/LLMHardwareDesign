#!/bin/bash
set -euo pipefail
root=/tmp/yzl-issue219-python3128-20261109
cd "$root"
tar -xzf /mnt/c/Users/wine10/AppData/Local/Codex/issue219-linux-python3128/libffi-3.4.6.tar.gz
cd libffi-3.4.6
./configure --prefix="$root/ffi" --disable-shared --with-pic > "$root/ffi-configure.log" 2>&1
make -j4 > "$root/ffi-build.log" 2>&1
make install > "$root/ffi-install.log" 2>&1
cd "$root/Python-3.12.8"
LIBFFI_CFLAGS="-I$root/ffi/include" LIBFFI_LIBS="$root/ffi/lib/libffi.a" ./configure --prefix="$root/install" --with-ensurepip=install > "$root/configure-ffi.log" 2>&1
make -j4 > "$root/build-ffi.log" 2>&1
make install > "$root/install-ffi.log" 2>&1
"$root/install/bin/python3.12" -c 'import ctypes; print(ctypes.sizeof(ctypes.c_int))'
"$root/install/bin/python3.12" -m test test_ctypes > "$root/ctypes-tests.log" 2>&1
cd /tmp/yzl-issue219-phase-round5-20261109
"$root/install/bin/python3.12" -X faulthandler -B -m unittest discover -p 'test_*.py' -q > tests-ffi.log 2>&1
